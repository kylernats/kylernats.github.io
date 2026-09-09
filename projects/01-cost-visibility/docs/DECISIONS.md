# Decision log — 01 Cost Visibility Dashboard

Each entry: the decision, the alternatives, and why this one. These are the
questions an interviewer asks, so the answers get written down while the
reasoning is fresh.

---

### Build the cost dashboard first, not last

**Alternatives:** build it last so it has real spend to display.

**Chose:** first. You instrument cost monitoring before you start spending,
not after. Building it first also protects the $200 credit while projects
02–05 get built.

**Tradeoff:** the dashboard is nearly empty at first. Accepted, and documented,
rather than hidden.

---

### Forecasted alert alongside actual thresholds

**Alternatives:** actual-spend thresholds only, which is the default most
people configure.

**Chose:** three actual thresholds (50/80/100%) plus a forecast alert at 100%.

**Why:** actual thresholds are backward-looking. They tell you money is already
gone. The forecast alert fires when the month is *projected* to exceed budget,
which is the only one that arrives while there is still time to act.

---

### Cost Management Reader, not Contributor

**Alternatives:** Reader, or Contributor, on the identity that reads cost data.

**Chose:** `Cost Management Reader`, scoped to the subscription.

**Why:** the identity needs to read billing data and nothing else. If it were
compromised, the blast radius is disclosure of a bill — not the ability to
create, modify, or delete resources. Reader would also work but grants
visibility into every resource's configuration, which is more than required.

---

### Storage left with public network access enabled

**Alternatives:** private endpoint, or service endpoint with a VNet.

**Chose:** public network access on, with TLS 1.2 minimum, no public blob
access, and private container ACLs.

**Why:** the Cost Management export service writes from Azure's side and cannot
reach a fully locked-down account without private endpoints, which are not in
the free tier.

**This is a real gap, not a solved problem.** In an environment with a budget
the fix is a private endpoint. Documented here rather than papered over.

---

### LRS, not GRS, for the export storage

**Alternatives:** GRS or ZRS for redundancy.

**Chose:** LRS.

**Why:** the data is a daily regenerating export of cost data that Azure also
holds. Losing a region's copy means re-running an export, not losing anything
irreplaceable. Paying for geo-redundancy here would be spending money to
protect against a scenario with no real consequence — which is itself the kind
of decision this project is about.
