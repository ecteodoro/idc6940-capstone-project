"""Build the capstone presentation on the UWF Blue layout.

Usage: python build_pptx.py TEMPLATE.pptx OUTPUT.pptx
All numbers come from paper/full_paper.tex (tables: policy, frontier, paired, sens, valclass, valprice).
"""
import copy
import sys
from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

NAVY, GREEN, LIGHT = "0E2D6D", "1C9C48", "EAF0FA"
BLUE, GRAY, ORANGE, WHITE = "5C7BB8", "4A5568", "C8553D", "FFFFFF"
FONT = "Arial"
X0, W = 2.2, 7.3  # content column (the layout's left sidebar ends at 1.9")

template, out = sys.argv[1], sys.argv[2]
prs = Presentation(template)
bg_src = prs.slides[1]
bg_rid = bg_src._element.find(".//" + qn("a:blip")).get(qn("r:embed"))
bg_part = bg_src.part.related_part(bg_rid)
bg_xml = copy.deepcopy(bg_src._element.find(qn("p:cSld")).find(qn("p:bg")))
layout_content = prs.slide_layouts[1]


def rgb(h):
    return RGBColor.from_string(h)


def tb(slide, x, y, w, h, paras, size=14, color=NAVY, bold=False, align=PP_ALIGN.LEFT,
       anchor=MSO_ANCHOR.TOP, name=None, space_after=4):
    """paras: str | list of (str | list of (text, {bold,color,size}) runs)."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    if isinstance(paras, str):
        paras = [paras]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(space_after)
        runs = [(p, {})] if isinstance(p, str) else p
        for text, o in runs:
            r = para.add_run()
            r.text = text
            f = r.font
            f.name = FONT
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.color.rgb = rgb(o.get("color", color))
    return box


def card(slide, x, y, w, h, fill=LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    s.line.fill.background()
    s.shadow.inherit = False
    if name:
        s.name = name
    return s


def circle(slide, x, y, d, label, fill=NAVY, size=14):
    c = card(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    tf = c.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size, r.font.bold, r.font.name = Pt(size), True, FONT
    r.font.color.rgb = rgb(WHITE)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return c


def new_slide(title, notes, number):
    s = prs.slides.add_slide(layout_content)
    rid = s.part.relate_to(bg_part, RT.IMAGE)
    bg = copy.deepcopy(bg_xml)
    bg.find(".//" + qn("a:blip")).set(qn("r:embed"), rid)
    cSld = s._element.find(qn("p:cSld"))
    cSld.insert(0, bg)
    tb(s, X0, 0.3, W, 0.62, title, size=26, bold=True, anchor=MSO_ANCHOR.MIDDLE, name="Title")
    tb(s, 8.9, 5.12, 0.6, 0.3, str(number), size=11, color=GRAY, align=PP_ALIGN.RIGHT, name="Slide number")
    s.notes_slide.notes_text_frame.text = notes
    # fade transition (schema order: cSld, clrMapOvr, transition)
    trans = etree.SubElement(s._element, qn("p:transition"))
    trans.set("spd", "med")
    etree.SubElement(trans, qn("p:fade"))
    return s


def style_chart(chart, size=11):
    chart.font.size = Pt(size)
    chart.font.name = FONT
    chart.font.color.rgb = rgb(GRAY)


def bar_chart(slide, x, y, w, h, cats, vals, colors, fmt, horizontal=False, size=11, vmin=None, vmax=None,
              gap=60):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("Series", vals)
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    gf = slide.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    style_chart(ch, size)
    ch.has_legend = False
    ch.has_title = False
    pl = ch.plots[0]
    pl.gap_width = gap
    pl.has_data_labels = True
    dl = pl.data_labels
    dl.number_format, dl.number_format_is_linked = fmt, False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.bold, dl.font.color.rgb = Pt(size), True, rgb(NAVY)
    pl.series[0].invert_if_negative = False
    for i, c in enumerate(colors):
        pt = pl.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(c)
    for dpt in pl.series[0]._element.findall(qn("c:dPt")):
        inv = etree.Element(qn("c:invertIfNegative"))
        inv.set("val", "0")
        dpt.find(qn("c:idx")).addnext(inv)
    va = ch.value_axis
    va.visible = False
    va.has_major_gridlines = False
    if vmin is not None:
        va.minimum_scale = vmin
    if vmax is not None:
        va.maximum_scale = vmax
    ca = ch.category_axis
    ca.format.line.color.rgb = rgb("B8C2D6")
    ca.tick_labels.font.size = Pt(size)
    ca.has_major_gridlines = False
    if horizontal:
        ca.reverse_order = True
        ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    return ch


# ---------------------------------------------------------------- slide 1: title
t = prs.slides[0]
for sh in t.placeholders:
    if sh.placeholder_format.idx == 0:
        sh.text_frame.text = "Optimizing Auction Floor Prices Under the Conversion–Revenue Tradeoff"
        for p in sh.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(24)
    elif sh.placeholder_format.idx == 1:
        sh.text_frame.text = "Ecil Teodoro · IDC6940 Capstone"
        for p in sh.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(14)
t.notes_slide.notes_text_frame.text = (
    "[0:30] Introduce yourself and the one-sentence project: how a seller should set the minimum "
    "acceptable price, the floor, on each vehicle at a wholesale auction when a minimum share of "
    "vehicles has to sell. The work is a simulation study calibrated to public data.")

# ---------------------------------------------------------------- slide 2: motivation
s = new_slide("Why the floor price matters", (
    "[1:15] A floor is the minimum offer the seller will accept. Raise it and a vehicle that sells brings in more, "
    "but fewer vehicles sell. A no-sale delays payment and adds holding, transport and rerun costs, but the seller "
    "still owns a car with resale value. So average sale price alone ignores the no-sales, and conversion alone "
    "ignores what each sale is worth. We need a measure that counts both: seller value."), 2)
cw = 3.55
card(s, X0, 1.15, cw, 1.75)
tb(s, X0 + 0.15, 1.22, cw - 0.3, 0.4, "Higher floor", size=16, bold=True, color=GREEN)
tb(s, X0 + 0.15, 1.62, cw - 0.3, 1.2, "Vehicles that sell bring in more money", size=15)
card(s, X0 + cw + 0.2, 1.15, cw, 1.75)
tb(s, X0 + cw + 0.35, 1.22, cw - 0.3, 0.4, "Higher floor", size=16, bold=True, color=ORANGE)
tb(s, X0 + cw + 0.35, 1.62, cw - 0.3, 1.2, "Fewer vehicles sell: delay, holding and rerun costs", size=15)
card(s, X0, 3.1, W, 1.1, fill=NAVY)
tb(s, X0 + 0.2, 3.15, W - 0.4, 1.0,
   [[("Seller value", {"bold": True, "color": WHITE, "size": 17}),
     (" = net proceeds when a vehicle sells + the value of keeping it when it does not", {"color": WHITE, "size": 15})]],
   anchor=MSO_ANCHOR.MIDDLE)
tb(s, X0, 4.35, W, 0.7,
   "Goal: choose a floor for each vehicle to maximize expected seller value while at least a target share of vehicles sells.",
   size=14, color=GRAY)

# ---------------------------------------------------------------- slide 3: question + approach
s = new_slide("Research question and approach", (
    "[1:00] The question is how to choose floors across a portfolio to maximize expected value subject to a minimum "
    "expected conversion. The approach has four steps: calibrate a synthetic auction generator to public Larsen data, "
    "estimate sale probability and price, optimize floors with a mixed-integer program, and evaluate against simple rules "
    "and an oracle that knows the true responses. Related work: Myerson on optimal auctions, Guan and Xu on reserves as "
    "signals, Larsen on bargaining after wholesale auctions, and Elmachtoub and Grigas on predict-then-optimize."), 3)
steps = [("1", "Calibrate", "Synthetic auctions matched to public Larsen data"),
         ("2", "Estimate", "Sale probability and price given the floor"),
         ("3", "Optimize", "Mixed-integer program picks each floor"),
         ("4", "Evaluate", "Compare with simple rules and an oracle")]
sw = 1.72
for i, (n, h, d) in enumerate(steps):
    x = X0 + i * (sw + 0.14)
    card(s, x, 1.2, sw, 2.2)
    circle(s, x + 0.15, 1.35, 0.45, n)
    tb(s, x + 0.1, 1.9, sw - 0.2, 0.4, h, size=16, bold=True)
    tb(s, x + 0.1, 2.3, sw - 0.2, 1.1, d, size=13, color=GRAY)
tb(s, X0, 3.6, W, 0.35, "Builds on", size=14, bold=True, color=GREEN)
tb(s, X0, 3.95, W, 1.1,
   ["Myerson and Riley: optimal auctions and reserve prices",
    "Guan and Xu: reserves can signal seller information",
    "Larsen: bargaining after wholesale auctions",
    "Elmachtoub and Grigas: prediction judged by decisions"], size=12, color=GRAY, space_after=1)

# ---------------------------------------------------------------- slide 4: data
s = new_slide("Data: public records, simulated auctions", (
    "[1:15] The calibration source is Larsen's public replication archive of wholesale used-vehicle auctions. Dealer and "
    "fleet/lease sellers are calibrated separately because rules and vehicles differ. Real records cannot show what "
    "would have happened at a different floor, so I simulate. Each dataset has 50,000 vehicles and 30 independent "
    "datasets are generated per environment. The 2-by-2 grid is the key design: prices either must exceed the floor or "
    "can bargain below it, and floors were either historically assigned, with a private seller signal, or randomized."), 4)
tb(s, X0, 1.1, 2.65, 3.9,
   [[("Source", {"bold": True, "color": GREEN})],
    "Larsen public archive; dealer and fleet/lease runs calibrated separately",
    [("Simulated", {"bold": True, "color": GREEN})],
    "50,000 vehicles per dataset, 30 datasets per environment",
    [("Assumed", {"bold": True, "color": GREEN})],
    "Floor effect on sales (slope \u22124.0 on the logit scale), costs, retained value"],
   size=12, color=NAVY, space_after=5)
gx, gy, gw, gh = 5.0, 1.45, 2.2, 1.45
tb(s, gx, 1.05, gw, 0.35, "Historical floors", size=12, bold=True, color=GRAY, align=PP_ALIGN.CENTER)
tb(s, gx + gw + 0.1, 1.05, gw, 0.35, "Randomized floors", size=12, bold=True, color=GRAY, align=PP_ALIGN.CENTER)
rows = [("Binding price", "Sale price must exceed the floor"), ("Bargaining", "Sale can close below the floor")]
for r, (head, body) in enumerate(rows):
    for c in range(2):
        x, y = gx + c * (gw + 0.1), gy + r * (gh + 0.1)
        card(s, x, y, gw, gh, fill=LIGHT if (r + c) % 2 == 0 else "DCE6F7")
        tb(s, x + 0.08, y + 0.1, gw - 0.16, gh - 0.2,
           [[(head, {"bold": True, "size": 13})], [(body, {"size": 12, "color": GRAY})]],
           anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
tb(s, gx, 4.6, 2 * gw + 0.1, 0.4, "4 environments \u00d7 30 datasets = 120 refits", size=12, color=GRAY,
   align=PP_ALIGN.CENTER)

# ---------------------------------------------------------------- slide 5: model
s = new_slide("Model: two parts and one value", (
    "[1:30] For each vehicle and candidate floor ratio a, which is floor over a valuation benchmark, I estimate two things. "
    "First, the probability of sale q, with a penalized logistic regression using a spline in the floor ratio. Second, "
    "the price given a sale, a log-premium regression with a retransformation correction. They combine into expected "
    "seller value: probability of sale times price net of fee, plus probability of no sale times the value of keeping the car "
    "net of holding cost. I also fit boosted models as a flexible comparison and kept whichever won on validation data: "
    "logistic for sale probability, boosted for price."), 5)
fx = [("Sale probability", "logit q(a) = β₀ + s(a) + X′β", "Logistic + spline kept (log loss 0.526 vs boosted 0.529)"),
      ("Price if sold", "log(P/m) = γ₀ + h(a) + X′γ + ε", "Boosted kept (RMSE $112 vs ridge $147)")]
for i, (h, f, n) in enumerate(fx):
    x = X0 + i * (cw + 0.2)
    card(s, x, 1.15, cw, 1.8)
    tb(s, x + 0.12, 1.2, cw - 0.24, 0.35, h, size=14, bold=True, color=GREEN)
    tb(s, x + 0.12, 1.58, cw - 0.24, 0.7, f, size=14, bold=True)
    tb(s, x + 0.12, 2.2, cw - 0.24, 0.7, n, size=12, color=GRAY)
card(s, X0, 3.2, W, 1.15, fill=NAVY)
tb(s, X0 + 0.15, 3.25, W - 0.3, 1.05,
   [[("U(a) = q(a) · [ p(a) − fee ]  +  [ 1 − q(a) ] · ( retained value − holding cost )",
      {"color": WHITE, "bold": True, "size": 14})]], anchor=MSO_ANCHOR.MIDDLE)
tb(s, X0, 4.45, W, 0.45, "a = floor / benchmark value · m = benchmark · p = expected price if sold",
   size=11, color=GRAY)

# ---------------------------------------------------------------- slide 6: optimization
s = new_slide("Optimization: one floor per vehicle", (
    "[1:15] With predictions fixed, choosing floors is a mixed-integer linear program. Each vehicle gets exactly one of "
    "27 candidate floors, and the portfolio's expected conversion has to reach the target tau. I solve it with HiGHS through "
    "SciPy. Raising tau traces a frontier of value against conversion. If tau is higher than the best conversion any set of "
    "candidates can reach, the problem is reported as infeasible. Important: the constraint is on expected conversion, not "
    "the realized outcome of one auction."), 6)
card(s, X0, 1.15, 4.2, 2.65, fill=NAVY)
tb(s, X0 + 0.15, 1.22, 3.9, 2.5,
   [[("maximize", {"color": "9DB4E8", "size": 12})],
    [("Σᵢ Σₖ zᵢₖ · Uᵢ(aᵢₖ)", {"color": WHITE, "bold": True, "size": 15})],
    [("subject to", {"color": "9DB4E8", "size": 12})],
    [("Σₖ zᵢₖ = 1   for every vehicle i", {"color": WHITE, "size": 14})],
    [("Σᵢ Σₖ zᵢₖ · qᵢ(aᵢₖ) ≥ Nτ", {"color": WHITE, "size": 14})],
    [("zᵢₖ ∈ {0, 1}", {"color": WHITE, "size": 14})]], space_after=6)
facts = [("27", "candidate floors per vehicle"), ("200", "vehicles per portfolio"), ("40–80%", "conversion targets τ")]
for i, (n, d) in enumerate(facts):
    y = 1.15 + i * 0.9
    card(s, X0 + 4.4, y, 2.9, 0.8)
    tb(s, X0 + 4.5, y + 0.02, 1.15, 0.76, n, size=20, bold=True, color=GREEN, anchor=MSO_ANCHOR.MIDDLE)
    tb(s, X0 + 5.6, y + 0.02, 1.65, 0.76, d, size=12, color=NAVY, anchor=MSO_ANCHOR.MIDDLE)
tb(s, X0, 4.0, W, 1.0,
   ["Solver: HiGHS through SciPy, 30-second limit, optimality gap 10⁻⁶",
    "Candidates come from floors seen in comparable training vehicles, plus common ratios and proportional cuts"],
   size=13, color=GRAY, space_after=3)

# ---------------------------------------------------------------- slide 7: evaluation
s = new_slide("How the policies are compared", (
    "[1:00] Five policies are evaluated on the same 200 test vehicles in each replication. Assigned floors, a common ratio "
    "for every vehicle, a proportional reduction, the optimized floors, and the oracle. The oracle uses the generator's "
    "true response functions with the same candidate floors and the same observable information; the private signal is "
    "integrated out, so it has no peek at it. Regret is oracle value minus policy value. Data are split chronologically, 60 "
    "training, 20 validation, 20 test, and models are refit in every replication."), 7)
pol = [("Assigned floor", "Keep the historical floor (clipped to supported bounds)", GRAY),
       ("Common ratio", "Same floor-to-benchmark ratio for every vehicle", BLUE),
       ("Proportional reduction", "Cut each assigned floor by a fixed percentage", BLUE),
       ("Optimized", "Mixed-integer program on fitted models", GREEN),
       ("Oracle", "True response functions; private signal integrated out", NAVY)]
for i, (h, d, c) in enumerate(pol):
    y = 1.1 + i * 0.62
    card(s, X0, y, 5.4, 0.54)
    circle(s, X0 + 0.08, y + 0.07, 0.4, str(i + 1), fill=c, size=13)
    tb(s, X0 + 0.58, y, 4.8, 0.54,
       [[(h + "  ", {"bold": True, "size": 13}), (d, {"size": 11, "color": GRAY})]], anchor=MSO_ANCHOR.MIDDLE)
card(s, X0 + 5.55, 1.1, 1.75, 3.0)
tb(s, X0 + 5.62, 1.15, 1.62, 2.9,
   [[("Regret", {"bold": True, "color": GREEN, "size": 14})],
    "oracle value − policy value",
    [("Split", {"bold": True, "color": GREEN, "size": 14})],
    "60 / 20 / 20 by date",
    [("Replications", {"bold": True, "color": GREEN, "size": 14})],
    "30 per environment"], size=11, color=NAVY, space_after=3)
tb(s, X0, 4.3, W, 0.7, "Policies that miss the conversion target are not treated as valid alternatives.", size=13,
   color=GRAY)

# ---------------------------------------------------------------- slide 8: code
s = new_slide("Code sources and implementation", (
    "[1:30] The calibration data come from Larsen's public archive; his MATLAB and Stata code estimates a structural "
    "bargaining model and I did not reuse it. The pipeline here is Python in six notebooks plus a helper module and tests. "
    "Three challenges: first, an early test period had been inspected before the protocol was final, so I retired it, "
    "replaced a linear calendar trend with seasonal terms, and ran all reported results on independent datasets with "
    "separate seeds. Second, the oracle needs numerical integration, so I checked it two ways. Third, reproducibility: "
    "source-file hashes are verified, and the datasets for every replication are provided."), 8)
card(s, X0, 1.1, 3.0, 3.95)
tb(s, X0 + 0.12, 1.15, 2.8, 0.35, "Pipeline", size=14, bold=True, color=GREEN)
tb(s, X0 + 0.12, 1.52, 2.8, 3.5,
   ["01  Source audit", "02  Calibration and simulation", "03  Train and evaluate", "04  Probability calibration",
    "05  Policy study", "06  Results and report", "auction_helpers.py + tests"], size=12, space_after=5)
tb(s, X0 + 3.15, 1.1, 4.15, 0.3, "Challenges and what I did", size=14, bold=True, color=GREEN)
ch = [("Test period inspected early", "Retired it; seasonal terms replace the calendar trend; fresh datasets and seeds"),
      ("Oracle needs integration", "41 vs 81 nodes: max conversion error 0.0005; Monte Carlo agrees"),
      ("Reproducibility", "Source hashes verified; per-replication datasets shared")]
for i, (h, d) in enumerate(ch):
    y = 1.45 + i * 1.12
    card(s, X0 + 3.15, y, 4.15, 1.02)
    tb(s, X0 + 3.25, y + 0.03, 3.95, 0.3, h, size=13, bold=True)
    tb(s, X0 + 3.25, y + 0.35, 3.95, 0.65, d, size=11, color=GRAY)
tb(s, X0 + 3.15, 4.85, 4.15, 0.3, "Python · NumPy · pandas · scikit-learn · SciPy", size=10, color=GRAY)

# ---------------------------------------------------------------- slide 9: prediction results
s = new_slide("Results: prediction", (
    "[1:15] The sale model ranks vehicles well, with an AUC of 0.82. Dealer conversion is predicted almost exactly. But "
    "fleet and lease conversion is predicted too low, for example 0.58 predicted against 0.69 observed in the 1.0 to 1.25 "
    "floor band. The validation-based correction kept the raw probabilities in 116 of 120 replications, so this bias "
    "carries into the optimizer. That matters on the next slide."), 9)
stats = [("0.82", "AUC of the sale model"), ("$112", "price RMSE, boosted model")]
for i, (n, d) in enumerate(stats):
    y = 1.15 + i * 1.4
    card(s, X0, y, 2.5, 1.25)
    tb(s, X0 + 0.1, y + 0.05, 2.3, 0.65, n, size=30, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
    tb(s, X0 + 0.1, y + 0.7, 2.3, 0.5, d, size=12, color=NAVY, align=PP_ALIGN.CENTER)
tb(s, X0 + 2.75, 1.05, 4.5, 0.55, "Held-out conversion: predicted vs observed", size=14, bold=True)
cd = CategoryChartData()
cd.categories = ["Dealer\n(floor 0.75–1.0)", "Fleet/lease\n(floor 1.0–1.25)"]
cd.add_series("Predicted", (0.510, 0.584))
cd.add_series("Observed", (0.509, 0.688))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(X0 + 2.75), Inches(1.55), Inches(4.55), Inches(3.0), cd)
c = gf.chart
style_chart(c)
c.has_legend, c.legend.position, c.legend.include_in_layout = True, XL_LEGEND_POSITION.BOTTOM, False
c.value_axis.visible = False
c.value_axis.has_major_gridlines = False
c.value_axis.minimum_scale, c.value_axis.maximum_scale = 0, 0.85
pl = c.plots[0]
pl.gap_width, pl.overlap = 70, -5
pl.has_data_labels = True
pl.data_labels.number_format, pl.data_labels.number_format_is_linked = "0.00", False
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
pl.data_labels.font.size, pl.data_labels.font.bold = Pt(12), True
for ser, col in zip(pl.series, (BLUE, NAVY)):
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = rgb(col)
tb(s, X0 + 2.75, 4.6, 4.55, 0.45, "Fleet/lease is under-predicted, so the optimizer over-delivers conversion", size=11,
   color=ORANGE, bold=True)

# ---------------------------------------------------------------- slide 10: policy results
s = new_slide("Results: policies at 60% conversion", (
    "[1:30] This is the main result. Expected value per vehicle: optimized 8,001 dollars against 7,662 for the common "
    "ratio and 7,091 for the proportional reduction, and 8,264 for the oracle. The assigned floors look similar to the "
    "common ratio in value, but their expected conversion is only 0.51, so they never meet the requirement. Paired "
    "within-replication, optimized beats the common ratio by about 340 dollars, roughly 4 percent. Regret to the oracle "
    "is 262 dollars versus 602 and 1,219. Caveat: the optimizer delivers 0.657 conversion against 0.60 needed, which is "
    "the fleet/lease under-prediction showing up."), 10)
cats = ["Prop.\nreduction", "Common\nratio", "Assigned\n(misses 60%)", "Optimized", "Oracle"]
vals = (7091, 7662, 7663, 8001, 8264)
bar_chart(s, X0, 1.0, 4.7, 3.9, cats, vals, [BLUE, BLUE, "B8C2D6", GREEN, NAVY], "$#,##0", size=11, vmin=6000,
          vmax=8700)
tb(s, X0, 4.85, 4.7, 0.3, "Expected seller value per vehicle (axis starts at $6,000)", size=10, color=GRAY)
big = [("+$340", "vs common ratio, about 4%"), ("$262", "regret, vs $602 and $1,219"), ]
for i, (n, d) in enumerate(big):
    y = 1.1 + i * 1.3
    card(s, X0 + 4.9, y, 2.4, 1.15)
    tb(s, X0 + 4.95, y + 0.03, 2.3, 0.55, n, size=26, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
    tb(s, X0 + 4.95, y + 0.62, 2.3, 0.5, d, size=11, color=NAVY, align=PP_ALIGN.CENTER)
card(s, X0 + 4.9, 3.7, 2.4, 1.2, fill=NAVY)
tb(s, X0 + 4.97, 3.72, 2.26, 1.16, "Optimized conversion 0.657 vs 0.60 required; oracle sits at 0.60", size=11,
   color=WHITE, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)

# ---------------------------------------------------------------- slide 11: frontier
s = new_slide("Results: the cost of more conversion", (
    "[1:15] Raising the conversion requirement costs value, and the cost accelerates. Going from 40 to 50 percent costs about "
    "134 dollars per vehicle, 50 to 60 about 331, and 60 to 70 about 679. At 80 percent the optimizer found a feasible "
    "solution in only 27 percent of replications, so that point is mostly infeasible. This is the frontier a seller would "
    "use to decide how much conversion is worth."), 11)
cd = CategoryChartData()
cd.categories = ["40%", "50%", "60%", "70%", "80%*"]
cd.add_series("Expected value", (8466, 8332, 8001, 7322, 5763))
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(X0), Inches(1.0), Inches(4.7), Inches(3.9), cd)
c = gf.chart
style_chart(c)
c.has_title = False
c.has_legend = False
c.value_axis.has_major_gridlines = True
c.value_axis.major_gridlines.format.line.color.rgb = rgb("E1E7F2")
c.value_axis.minimum_scale, c.value_axis.maximum_scale = 5000, 9000
c.value_axis.tick_labels.number_format, c.value_axis.tick_labels.number_format_is_linked = "$#,##0", False
c.value_axis.format.line.fill.background()
ser = c.plots[0].series[0]
ser.format.line.color.rgb = rgb(GREEN)
ser.format.line.width = Pt(3)
ser.smooth = False
ser.marker.format.fill.solid()
ser.marker.format.fill.fore_color.rgb = rgb(NAVY)
ser.marker.size = 9
c.plots[0].has_data_labels = True
dl = c.plots[0].data_labels
dl.number_format, dl.number_format_is_linked = "$#,##0", False
dl.position = XL_LABEL_POSITION.ABOVE
dl.font.size, dl.font.bold, dl.font.color.rgb = Pt(11), True, rgb(NAVY)
sdl = ser.data_labels
sdl.show_value = True
sdl.number_format, sdl.number_format_is_linked = "$#,##0", False
sdl.position = XL_LABEL_POSITION.ABOVE
sdl.font.size, sdl.font.bold, sdl.font.color.rgb = Pt(11), True, rgb(NAVY)
last = ser.points[4].data_label
last.position = XL_LABEL_POSITION.LEFT
last.text_frame.text = "$5,763"
r0 = last.text_frame.paragraphs[0].runs[0]
r0.font.size, r0.font.bold, r0.font.color.rgb = Pt(11), True, rgb(NAVY)
tb(s, X0, 4.85, 4.7, 0.3, "Requirement on expected conversion · *feasible in 27% of replications", size=10,
   color=GRAY)
tb(s, X0 + 4.9, 1.05, 2.4, 0.3, "Cost of +10 points", size=13, bold=True, color=GREEN)
for i, (rng, v) in enumerate([("40 → 50%", "$134"), ("50 → 60%", "$331"), ("60 → 70%", "$679")]):
    y = 1.45 + i * 1.1
    card(s, X0 + 4.9, y, 2.4, 0.95)
    tb(s, X0 + 4.95, y + 0.04, 2.3, 0.3, rng, size=11, color=GRAY, align=PP_ALIGN.CENTER)
    tb(s, X0 + 4.95, y + 0.34, 2.3, 0.55, v, size=24, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
tb(s, X0 + 4.9, 4.7, 2.4, 0.4, "per vehicle", size=11, color=GRAY)

# ---------------------------------------------------------------- slide 12: robustness
s = new_slide("Results: does the gain hold up?", (
    "[1:15] Left: the gain over the common ratio is about the same with randomized floors, 350 dollars, as with historical "
    "floors, 340, so in this simulation it does not depend on confounding between floors and outcomes. It is about half as "
    "large when bargaining below the floor is allowed. Right: the assumptions that matter most are demand and retained value, "
    "plus or minus 400 to 700 dollars; holding cost moves value by about 100 dollars at most. In practice, effort should go "
    "into demand and retained value, not holding cost."), 12)
tb(s, X0, 1.0, 3.5, 0.55, "Gain over common ratio ($/vehicle)", size=13, bold=True)
bar_chart(s, X0, 1.45, 3.5, 3.4, ["Binding\nhistorical", "Binding\nrandom.", "Bargain.\nhistorical", "Bargain.\nrandom."],
          (339.7, 349.6, 181.9, 179.3), [GREEN, GREEN, BLUE, BLUE], "$#,##0", size=10, vmin=0, vmax=420, gap=50)
tb(s, X0 + 3.7, 1.0, 3.6, 0.55, "Change in value when one assumption moves", size=13, bold=True)
bar_chart(s, X0 + 3.7, 1.45, 3.6, 3.4,
          ["Weak demand", "Strong demand", "Retained 0.75", "Retained 0.95", "Strong priv. info", "High holding cost"],
          (-730, 642, -369, 378, -104, -103), [ORANGE, GREEN, ORANGE, GREEN, ORANGE, ORANGE], "$#,##0;-$#,##0",
          horizontal=True, size=10, vmin=-1250, vmax=950, gap=40)

# ---------------------------------------------------------------- slide 13: conclusion
s = new_slide("Conclusions and next steps", (
    "[1:15] In the simulated environments, optimized floors earned about 340 dollars more per vehicle than a common ratio at a "
    "60 percent requirement and came within 262 dollars of the oracle. The limits matter: floor response is an assumption, "
    "the private information is simulated, and nothing here is causal evidence about real auctions. Next steps: test "
    "decision-focused training, extend to repeated auctions, and validate on real auction outcomes. [Then questions.]"), 13)
cols = [("Findings", GREEN, ["+$340 per vehicle vs a common ratio at 60%", "Within $262 of the oracle",
                            "Cost of conversion rises sharply"]),
        ("Limits", ORANGE, ["Floor response is assumed", "Private information is simulated",
                            "Conversion under-predicted for fleet/lease"]),
        ("Next", BLUE, ["Decision-focused training", "Repeated auctions (up to 3 attempts)",
                        "Validate on real auction data"])]
cw3 = 2.33
for i, (h, c, items) in enumerate(cols):
    x = X0 + i * (cw3 + 0.155)
    card(s, x, 1.15, cw3, 2.6)
    circle(s, x + 0.12, 1.27, 0.4, str(i + 1), fill=c, size=13)
    tb(s, x + 0.6, 1.27, cw3 - 0.7, 0.4, h, size=16, bold=True, color=c, anchor=MSO_ANCHOR.MIDDLE)
    tb(s, x + 0.12, 1.8, cw3 - 0.24, 2.4, items, size=12, space_after=7)
card(s, X0, 3.95, W, 0.75, fill=NAVY)
tb(s, X0 + 0.15, 3.97, W - 0.3, 0.71, "Results apply to the simulated environments; real-auction performance is still an empirical question.",
   size=12, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- slide 14: questions
s = new_slide("Questions?", (
    "[0:15] Thank you. Backup: full figures, sensitivity table and bootstrap results are in the paper."), 14)
tb(s, X0, 1.6, W, 1.0, "Thank you", size=40, bold=True)
tb(s, X0, 2.7, W, 1.6,
   ["Ecil Teodoro", "Department of Mathematics and Statistics, University of West Florida",
    "Code, datasets and paper: project repository (idc6940-capstone-project)"], size=14, color=GRAY)

# ---------------------------------------------------------------- drop the unused template slide 2
sldIdLst = prs.slides._sldIdLst
first_content = sldIdLst[1]
prs.part.drop_rel(first_content.get(qn("r:id")))
sldIdLst.remove(first_content)

prs.save(out)
print("saved", out, len(prs.slides), "slides")
