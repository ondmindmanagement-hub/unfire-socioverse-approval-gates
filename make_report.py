#!/usr/bin/env python3
"""Create a provisional, reproducible 4-page SocioVerse Challenge research report."""
import json, statistics
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, KeepTogether
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
NATIVE = ROOT/"trajectory"/"native"/"native_summary.json"
DEST = ROOT/"reports"/"TrackC-UnfireResearch-HumanApproval-Report.pdf"
DEST.parent.mkdir(parents=True, exist_ok=True)
records = json.loads(NATIVE.read_text())
NAVY = colors.HexColor("#1C2936")
MID = colors.HexColor("#4A6173")
PALE = colors.HexColor("#ECF0F3")
GREY = colors.HexColor("#58636E")

style_title = ParagraphStyle("big", fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=NAVY, spaceAfter=14)
style_sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=11, leading=16, textColor=MID, spaceAfter=14)
style_head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=NAVY, spaceBefore=16, spaceAfter=8)
style_b = ParagraphStyle("body", fontName="Helvetica", fontSize=9.6, leading=14.4, spaceAfter=8, textColor=NAVY)
style_small = ParagraphStyle("small", fontName="Helvetica", fontSize=8.3, leading=11.7, spaceAfter=6, textColor=GREY)
style_note = ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=8.3, leading=12, textColor=MID, spaceAfter=8)
style_bullet = ParagraphStyle("bullet", parent=style_b, leftIndent=12, firstLineIndent=-8)

def P(txt, style=style_b):
    return Paragraph(txt, style)

def section(label, text=None):
    elements=[P(label,style_head)]
    if text: elements.append(P(text))
    return elements

def table(rows, widths, header=True):
    t=Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    ops=[("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),
         ("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),7),
         ("BOTTOMPADDING",(0,0),(-1,-1),7),("LINEBELOW",(0,-1),(-1,-1),0.6,colors.HexColor("#D1DADF")),
         ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F6F8F9")])]
    if header: ops += [("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]
    t.setStyle(TableStyle(ops))
    return t

def rows_for(arm,capacity):
    return [r["metrics"] for r in records if r["arm"]==arm and r["capacity"]==capacity]

def mean_stdev(arm,capacity,key):
    values=[float(v[key]) for v in rows_for(arm,capacity)]
    return statistics.mean(values), (statistics.stdev(values) if len(values)>1 else 0)
cases=[("No gate","ungated",8),("Static rule","static",8),("Capacity review: 8","capacity_review",8),("Capacity review: 2","capacity_review",2)]
numeric=[]
for label,arm,capacity in cases:
    unsafe,usd=mean_stdev(arm,capacity,"unsafe_action_rate")
    safe,ssd=mean_stdev(arm,capacity,"safe_task_completion")
    false,fsd=mean_stdev(arm,capacity,"false_denial_rate")
    exp,_=mean_stdev(arm,capacity,"review_expirations")
    numeric.append([label,f"{unsafe*100:.1f}%",f"{safe*100:.1f}%",f"{false*100:.1f}%",f"{exp:.1f}"])

doc=SimpleDocTemplate(str(DEST),pagesize=A4,rightMargin=19*mm,leftMargin=19*mm,topMargin=21*mm,bottomMargin=17*mm,
                      title="Unfire Research - Synthetic Human-Approval Gates - SocioVerse2 Track C",
                      author="Omar Baró / Unfire Research",subject="Preliminary scripted synthetic experiment")
story=[]
# PAGE 1
story += [P("Human Approval as a Controllable<br/>Simulation Mechanism",style_title),
          P("SocioVerse Challenge 2026 | Track C - Methodological and Systems Innovation",style_sub)]
story += [P("<b>Omar Baró</b> | Unfire Research | Independent developer, Spain",style_b),
          P("9 October 2026 | Preliminary synthetic experiment (not an official final submission)",style_note)]
story += section("Abstract")
story += [P("We implement a reproducible agent-based simulation of bounded approval capacity. "
            "Synthetic requests vary by risk, evidence completeness, a forbidden-action marker, arrival and deadline. "
            "We compare ungated execution, a static risk threshold and a scripted reviewer proxy. "
            "Twenty runs execute through the native SocioVerse2 engine (five prespecified seeds multiplied by four policy/capacity configurations). "
            "We report execution safety, valid-task completion, false denials and missed deadlines. "
            "<b>The results concern a deliberately simplified simulator, not real human reviewers or deployed AI agents.</b>")]
story += section("1. Research question and contribution")
story += [P("What is the measurable tradeoff between stopping unsafe synthetic actions and introducing review delay "
            "or mistaken rejection when review capacity is finite? The reusable contribution is a "
            "SocioVerse2-native Population / Environment / Decision / Collector implementation, "
            "a shared request generator and an auditable comparison protocol."),
          P("The comparison deliberately distinguishes model-free approval policy from model quality: "
            "the reviewer is a scripted mechanism, not a human subject or language model. "
            "Consequently this is a plumbing and methods test suitable for subsequent, more realistic experiments.")]
story += section("2. Hypotheses")
story += [P("H1: relative to no gate, explicit review of forbidden or risky requests decreases oracle-defined unsafe executions.",style_bullet),
          P("H2: a coarse static risk rule blocks some safe high-risk requests (false denials).",style_bullet),
          P("H3: reducing scripted reviewer capacity from eight to two requests per step increases deadline expirations and reduces safe-task completion.",style_bullet)]
story += [Spacer(1,8),P("No claims of operational benefit or causal effect on real organizations are made from these hypotheses or simulations.",style_note)]
story += [PageBreak()]
# PAGE 2
story += [P("Methods and experiment design",style_title)]
story += section("3. Population / Environment / Behavior (P/E/B)")
story += [P("<b>Population.</b> For each seed, 100 fixed synthetic requests with persistent identifiers, risk (high/low), "
            "evidence-completeness status, explicit forbidden marker, standard/urgent scheduling priority and a deadline. "
            "The identities are generated and contain no personal information."),
          P("<b>Environment.</b> Twelve arrival steps and a terminal-resolution horizon of 18 steps. "
            "Every comparison arm sees the same requests and initial state for each seed. "
            "The capacity parameter limits high-risk review decisions per step; late pending work expires."),
          P("<b>Behavior.</b> The no-gate arm executes immediately. Static policy denies all high-risk actions "
            "and executes lower-risk requests. The scripted-review arm immediately denies explicitly forbidden actions, "
            "allows low-risk requests and puts remaining high-risk requests into a bounded review queue. "
            "The proxy checks the synthetic evidence flag, not a human judgment.")]
story += section("4. Oracle and metrics")
story += [P("A request is oracle-safe when it is not explicitly forbidden and does not combine high risk with missing evidence. "
            "This definition is created by the simulation designer and is a key source of optimistic bias. "
            "Unsafe-action rate uses executed actions as its denominator; safe completion and false-denial rates "
            "use all oracle-safe requests as denominator."),
          P("Additional metrics include review expirations, latency in discrete simulated steps, the number of terminal outcomes, "
            "and breakdowns for the artificial urgency groups. They are not demographic fairness findings.")]
story += section("5. Prespecified protocol")
story += [P("Paired seeds: <b>11, 29, 47, 83 and 101</b>. A request set is generated once per seed and reused by every policy arm. "
            "Four variants: ungated, static, review capacity 8 and review capacity 2. "
            "All simulations run on SocioVerse2's native Python engine and persist DuckDB trajectories. "
            "An independent standard-library runner writes CSV/JSON metrics and integrity hashes."),
          P("All decisions use scripted logic, with <b>zero LLM calls</b> and an estimated model-API cost of <b>US $0</b>. "
            "There are no external human participants, private records or unlicensed data.")]
story += [PageBreak()]
# PAGE 3
story += [P("Results: descriptive synthetic outcomes",style_title)]
story += section("6. Aggregate rates across the five seeds")
head=["Policy / condition","Unsafe rate","Safe tasks","False denials","Avg. expired"]
table_rows=[head]
for r in numeric:
    table_rows.append([P(escape(r[0]),style_small),P(r[1],style_small),P(r[2],style_small),
                       P(r[3],style_small),P(r[4],style_small)])
story += [table(table_rows,[134,86,92,79,70]),
          Spacer(1,8),
          P("Each row averages five deterministic synthetic replications of 100 requests each. "
            "The rates are descriptive; the five random seeds are not a representative sample of real workplaces.",style_note)]
story += section("7. Interpretation")
story += [P("Ungated execution processes all incoming requests but allows oracle-defined unsafe requests. "
            "The static rule reduces many unsafe executions but rejects some oracle-safe high-risk requests. "
            "The review proxy performs better by construction because it reads the very flags used to define the oracle. "
            "At limited capacity, this proxy cannot finish every safe request by its deadline."),
          P("The difference between capacity 8 and capacity 2 measures queue mechanics, not human cognition. "
            "Review performance is therefore a <b>best-case scripted baseline</b> under the chosen oracle, "
            "not evidence that human reviewers would reach the same rates.")]
story += section("8. Reproducibility and QA evidence")
story += [P("The source repository contains Python execution code, native provider adapters, P/E/B configuration files, "
            "the exact seeds, per-request trajectories, SHA-256 file digests and a 20-run native summary. "
            "Eight unit tests check deterministic replay, identical paired workloads, terminal uniqueness, policy invariants "
            "and audit boundaries. The native engine passed all 20 configured runs."),
          P("Public repository: <link href='https://github.com/ondmindmanagement-hub/unfire-socioverse-approval-gates'>github.com/ondmindmanagement-hub/unfire-socioverse-approval-gates</link>",style_small)]
story += [PageBreak()]
# PAGE 4
story += [P("Limitations, validity and next work",style_title)]
story += section("9. Threats to validity")
story += [P("<b>Construct validity.</b> The oracle, requests and reviewer proxy share a deterministic synthetic rule. "
            "Apparent safety is partly tautological. The values are not calibrated to organization-specific policies."),
          P("<b>External validity.</b> No observed human approval times, organizational incentives, realistic malicious actors, "
            "LLM errors, asymmetric information or contested decisions are represented."),
          P("<b>Statistical validity.</b> Five seeds explore generator variation but do not produce population-level inference. "
            "No claim of statistical significance or effect sizes for real populations is warranted."),
          P("<b>Operational validity.</b> The demo omits reviewer authentication, override protocols, signed audit logs, privacy protection in actual user data, "
            "model latency, token expense and real-world integration risk.")]
story += section("10. Ethics and data use")
story += [P("All records are synthetic, without health data, financial account data, client events, identifying personal information "
            "or material copied from third-party users. No subjects are recruited. Priority labels are operational variables, "
            "not proxies for protected human traits.")]
story += section("11. Next experiments")
story += [P("First, add noisy reviewer classifications and intentional misclassification to avoid a perfect oracle. "
            "Second, vary action prevalence, review capacity, time limits and evidence availability across a broader grid. "
            "Third, include a human-controlled approval UI only after an ethical and methodological review. "
            "Fourth, compare real SocioVerse2 agent policies or LLM-controlled behavior with the scripted baseline "
            "while recording tokens, latency and cost.")]
story += section("12. Execution and submission status")
story += [P("At the SocioVerse2 repository root (Python 3.11+): "
            "<font name='Courier'>python -m studies.unfire_approval_gates.run_native</font>. "
            "Separately, <font name='Courier'>python -m unittest discover -s studies/unfire_approval_gates/tests</font>. "
            "The preliminary two-page proposal is ready but the competition-platform upload has not been confirmed. "
            "The final competition package additionally requires a short actual-run video and official submission before 31 October 2026 (UTC+8).")]
story += section("References and basis")
story += [P("SocioVerse2 open-source platform and Challenge 2026 official rules, socioverse.fudan-disc.com/challenge/; "
            "SocioVerse2 source repository (sii-research/SocioVerse2, Apache-2.0). "
            "Grimm et al. (2020), ODD protocol for describing agent-based and other simulation models, JASSS 23(2).",style_small),
          P("This document is a provisional research artifact, not a certified safety assessment or proof of competition acceptance.",style_note)]

def chrome(canvas, doc):
    canvas.saveState()
    w,h=A4
    canvas.setStrokeColor(colors.HexColor("#CED8DF"))
    canvas.line(19*mm,h-16*mm,w-19*mm,h-16*mm)
    canvas.setFont("Helvetica-Bold",7.5)
    canvas.setFillColor(MID)
    canvas.drawString(19*mm,h-12*mm,"UNFIRE RESEARCH  /  SOCIOVERSE CHALLENGE 2026")
    canvas.line(19*mm,14*mm,w-19*mm,14*mm)
    canvas.setFont("Helvetica",7.5)
    canvas.drawString(19*mm,10*mm,"SYNTHETIC EXPERIMENT  |  PROVISIONAL REPORT")
    canvas.drawRightString(w-19*mm,10*mm,str(doc.page))
    canvas.restoreState()

doc.build(story,onFirstPage=chrome,onLaterPages=chrome)
print("REPORT",DEST)
print("BYTES",DEST.stat().st_size)
print("AGGREGATE",numeric)
