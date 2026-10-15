"""Shared modelling helpers used by notebooks 03-05.

Functions here take notebook configuration (feature lists, origin date, minimum
category count) as explicit arguments. Notebooks keep thin wrappers named
``features`` and ``preprocessing`` that bind their own globals.
"""
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix, eye, kron, vstack
from scipy.special import logit
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def make_features(d, origin, categorical, columns):
    x = d[['age', 'mileage', 'benchmark', 'floor_ratio'] + categorical].copy()
    x['log_mileage'] = np.log1p(x.mileage)
    x['log_benchmark'] = np.log(x.benchmark)
    x['calendar_days'] = (pd.to_datetime(d.auction_date) - origin).dt.days
    month = pd.to_datetime(d.auction_date).dt.month
    x['month_sin'] = np.sin(2 * np.pi * month / 12)
    x['month_cos'] = np.cos(2 * np.pi * month / 12)
    for col in categorical:
        x[col] = x[col].fillna('<missing>').astype(str)
    return x[columns]


class RestrictedCubicSpline(BaseEstimator, TransformerMixin):
    def __init__(self, quantiles=(.05, .35, .65, .95)):
        self.quantiles = quantiles

    def fit(self, X, y=None):
        values = np.asarray(X, dtype=float).reshape(-1)
        self.knots_ = np.quantile(values, self.quantiles)
        if len(np.unique(self.knots_)) != len(self.knots_):
            raise ValueError('Spline knots must be distinct')
        return self

    def transform(self, X):
        a = np.asarray(X, dtype=float).reshape(-1)
        k = self.knots_
        positive = lambda z: np.maximum(z, 0) ** 3
        basis = [a]
        for knot in k[:-2]:
            term = (positive(a - knot) - positive(a - k[-2]) * (k[-1] - knot) / (k[-1] - k[-2])
                    + positive(a - k[-1]) * (k[-2] - knot) / (k[-1] - k[-2])) / (k[-1] - k[0]) ** 2
            basis.append(term)
        return np.column_stack(basis)


def make_preprocessing(knots, numeric, categorical, min_category_count):
    floor_steps = [('imputer', SimpleImputer(strategy='median'))]
    if knots is not None:
        floor_steps.append(('spline', RestrictedCubicSpline(knots)))
    floor_steps.append(('scale', StandardScaler()))
    return ColumnTransformer([
        ('numeric', make_pipeline(SimpleImputer(strategy='median', add_indicator=True), StandardScaler()), numeric),
        ('floor', Pipeline(floor_steps), ['floor_ratio']),
        ('categories', OneHotEncoder(handle_unknown='infrequent_if_exist', min_frequency=min_category_count,
                                     sparse_output=False), categorical)], sparse_threshold=0)


def fit_correction(mode, q, groups, y):
    if mode == 'raw':
        return {'mode': mode}
    result = {'mode': mode, 'models': {}}
    keys = ['all'] if mode == 'global_sigmoid' else sorted(pd.Series(groups).unique())
    groups = np.asarray(groups)
    y = np.asarray(y)
    for key in keys:
        use = np.ones(len(q), dtype=bool) if key == 'all' else groups == key
        m = LogisticRegression(C=1000, max_iter=1000)
        m.fit(logit(np.clip(q[use], 1e-8, 1 - 1e-8)).reshape(-1, 1), y[use])
        result['models'][key] = m
    return result


def correct(correction, q, groups):
    if correction['mode'] == 'raw':
        return q
    result = np.empty(len(q))
    groups = np.asarray(groups)
    for key, m in correction['models'].items():
        use = np.ones(len(q), dtype=bool) if key == 'all' else groups == key
        if not use.any():
            continue
        result[use] = m.predict_proba(logit(np.clip(q[use], 1e-8, 1 - 1e-8)).reshape(-1, 1))[:, 1]
    if correction['mode'] == 'group_sigmoid' and not set(groups) <= set(correction['models']):
        raise ValueError('Unseen seller group requires an explicit calibration rule')
    return result


# --- Policy-study helpers (notebook 05) ---

def split_dates(d):
    counts=d.groupby('auction_date').size().cumsum()
    first=(counts-.6*len(d)).abs().idxmin();second=(counts-.8*len(d)).abs().idxmin()
    return (d[d.auction_date.le(first)].copy(),d[d.auction_date.gt(first)&d.auction_date.le(second)].copy(),d[d.auction_date.gt(second)].copy())


def age_band(d):return pd.cut(d.age,[-1,3,7,np.inf],labels=['young','middle','old']).astype(str)


def support_fit(train):
    t=train.assign(age_band=age_band(train));maps=[]
    for keys in [['seller_group','condition','age_band'],['seller_group','condition'],['seller_group']]:
        table=t.groupby(keys).floor_ratio.agg(count='size',low=lambda a:a.quantile(.05),high=lambda a:a.quantile(.95))
        maps.append((keys,table))
    return maps


def bounds_for(d,maps):
    t=d.assign(age_band=age_band(d));lo=[];hi=[];levels=[]
    for _,row in t.iterrows():
        for level,(keys,table) in enumerate(maps):
            key=tuple(str(row[k]) for k in keys);key=key[0] if len(key)==1 else key
            if key in table.index and table.loc[key,'count']>=100:
                entry=table.loc[key];break
        low=max(.25,float(entry.low));high=min(3.0,float(entry.high))
        if high<=low:raise ValueError('Empty supported operational interval')
        lo.append(low);hi.append(high);levels.append(level)
    return np.array(lo),np.array(hi),np.array(levels)


def candidates(d,maps,common,reduction):
    lo,hi,levels=bounds_for(d,maps)
    ref=np.clip(d.floor_ratio.to_numpy(),lo,hi)
    grid=lo[:,None]+(hi-lo)[:,None]*np.linspace(0,1,11)[None,:]
    common_grid=np.clip(np.broadcast_to(np.linspace(.65,1.4,9),(len(d),9)),lo[:,None],hi[:,None])
    reductions=np.array([0,.025,.05,.10,.15,.20])
    reduction_grid=np.clip(d.floor_ratio.to_numpy()[:,None]*(1-reductions[None,:]),lo[:,None],hi[:,None])
    return np.column_stack([grid,ref,common_grid,reduction_grid]),levels


def value(q,gross,d):
    return gross-q*d.known_sale_fee.to_numpy()[:,None]+(1-q)*(d.retained_value-d.holding_cost).to_numpy()[:,None]


def optimize(q,v,target):
    n,k=q.shape;maximum=q.max(axis=1).mean()
    if maximum<target-1e-10:return None,dict(status='infeasible',max_conversion=maximum,gap=None)
    matrix=vstack([kron(eye(n),np.ones((1,k))),csr_matrix(q.reshape(1,-1))]).tocsc()
    result=milp(-v.ravel()/1000,integrality=np.ones(n*k),bounds=Bounds(0,1),
      constraints=LinearConstraint(matrix,np.r_[np.ones(n),n*target],np.r_[np.ones(n),np.inf]),
      options={'time_limit':30,'mip_rel_gap':1e-6})
    info=dict(status=int(result.status),max_conversion=maximum,gap=float(result.mip_gap) if getattr(result,'mip_gap',None) is not None else None)
    if result.status!=0 or result.x is None:return None,info
    choice=result.x.reshape(n,k).argmax(axis=1)
    assert q[np.arange(n),choice].mean()>=target-1e-7
    return choice,info
