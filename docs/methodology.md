# Methodology

## Planning problem

The optimiser chooses four continuous capacities:

- solar PV power \(K_{pv}\);
- battery energy \(K_e\);
- battery power \(K_p\); and
- biogas generator power \(K_b\).

It simultaneously chooses hourly grid import/export, charging, discharging, state of charge, biogas generation, curtailment and unserved load. The reference year contains one day per month plus a separately weighted August outage day: 312 modelled hours representing 365 days.

## Energy conservation

For each hour \(t\):

\[
cf_tK_{pv}+G_t+D_t+B_t+U_t=L_t+C_t+X_t+Q_t.
\]

Here \(cf_t\) is solar capacity factor; \(G_t\) grid imports; \(D_t\) battery discharge; \(B_t\) biogas; \(U_t\) unserved demand; \(L_t\) load; \(C_t\) charging; \(X_t\) exports; and \(Q_t\) curtailment.

## Battery physics

\[
SOC_t=SOC_{t-1}+\eta_cC_t-D_t/\eta_d,
\]

with charge and discharge power no greater than \(K_p\), and state of charge bounded between 10% and 95% of \(K_e\). Each representative day is cyclic. The reference round-trip efficiency is 90%.

The model does not use binary charge/discharge states. Because storage losses and throughput cost are positive, simultaneous charging and discharging cannot improve the optimum under the reference objective. A project with negative prices or complex ancillary-service revenues would require mixed-integer controls.

## Biogas resource balance

Annual generation is limited by:

\[
E_b \leq M_fY_gx_{CH4}H_{CH4}\eta_e\times365,
\]

where \(M_f\) is feedstock tonnes/day, \(Y_g\) is specific biogas yield, \(x_{CH4}\) methane volume fraction, \(H_{CH4}\) methane energy content and \(\eta_e\) electrical conversion efficiency.

This corrects the legacy assumption that methane mass equals 60% of wet manure mass. The reference 60 Nm³/tonne yield is an illustrative screening input, not a claim about camel manure.

## Reliability

One regular August day is replaced by an outage day with six islanded evening hours. The resilient design includes an aggregate constraint requiring effectively zero unserved energy during that event. The event retains an annual weight of one day, so annual energy still reconciles to 365 days.

After sizing, the installed capacities are frozen and tested over a 36-case resilience envelope spanning three representative months, four outage start times and three durations. Each case is optimally redispatched with perfect foresight and may shed load at the configured value of lost load. The output reports served energy rather than converting these deterministic cases into a probability of reliability.

## Objective

The capacity-planning layer minimises equivalent annual cost:

\[
\min CRF\cdot CAPEX + FOM + \sum_t w_t(GridCost_t-ExportRevenue_t+BioCost_t+BatteryWear_t+VOLL\cdot U_t).
\]

Capital recovery factors use technology-specific lives and the project discount rate. Positive battery losses and wear cost create economically meaningful charge/discharge behavior.

## Lifecycle economics

The financial layer separates initial capital from annual operating cost. It models battery replacements at its assumed 12-year life, solar-output degradation as replacement grid energy, and constant real operating assumptions. Outputs include NPV, IRR, discounted payback and LCOE over 25 years.

These values are screening outputs. A finance-grade investment model would add debt/equity structure, tax, inflation, insurance, land, development costs, EPC contingency, working capital and terminal value.

## Sensitivity analysis

Nine cases vary grid tariff and specific biogas yield across 80%, 100% and 120%/140% multipliers. Biogas yield is highlighted because feedstock conversion—not manure mass alone—is the largest unresolved physical input inherited from the original study.
