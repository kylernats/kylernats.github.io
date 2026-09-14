# Decision log — 01 Cost Visibility Dashboard

What I decided, what else I considered, and why. Written down when I made the
call, not after.

---

### Build the cost dashboard first, not last

**Alternatives:** build it last so it has real spend to display.

**Chose:** first. Set up cost monitoring before spending, not after. It also
protects the $200 credit while I build projects 02-05.

**Tradeoff:** the dashboard is almost empty at the start.

---

### Forecasted alert alongside actual thresholds

**Alternatives:** actual-spend thresholds only, which is the default most
people configure.

**Chose:** three actual thresholds (50/80/100%) plus a forecast alert at 100%.

**Why:** actual thresholds only tell me money is already spent. The forecast
alert fires when the month is projected to go over, so I still have time to do
something about it.

---

### Cost Management Reader, not Contributor

**Alternatives:** Reader, or Contributor, on the identity that reads cost data.

**Chose:** `Cost Management Reader`, scoped to the subscription.

**Why:** it only needs to read billing data. If it got compromised, all someone
gets is a bill. Reader would work too, but it shows every resource's config,
which is more access than the job needs.

---

### Storage left with public network access enabled

**Alternatives:** private endpoint, or service endpoint with a VNet.

**Chose:** public network access on, with TLS 1.2 minimum, no public blob
access, and private container ACLs.

**Why:** the export service writes from Azure's side. It can't reach a locked
down account without private endpoints, and those aren't free.

This is a gap, not a fix. With a budget I'd use a private endpoint.

---

### LRS, not GRS, for the export storage

**Alternatives:** GRS or ZRS for redundancy.

**Chose:** LRS.

**Why:** the export regenerates daily and Azure holds the same data anyway. If I
lost a region's copy I'd re-run the export. Paying for geo-redundancy here would
be spending money on a problem I don't have.

---

### Redacting identifiers from published evidence

**Alternatives:** publish screenshots as taken. Microsoft's own documentation
shows subscription IDs freely, and a subscription ID is an identifier rather
than a credential — it grants nothing on its own.

**Chose:** blur the subscription ID, account email, and tenant domain
(`*.onmicrosoft.com`) in every published screenshot, and scrub the ID from
captured API output. `snapshot.sh` now does the scrub automatically so it
cannot be forgotten later.

**Why:** there's no reason to publish them. None of the three is secret on its
own, but together they're useful for targeted phishing and consent-grant attacks
against a tenant. Everything the screenshots are meant to prove still shows.

**Method:** pixelate first, then blur. A light blur on a fixed-width font can
often be read back. Downsampling removes the information instead of hiding it.
