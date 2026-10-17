/// Optional bounded recovery operator. Not installed in the production class set.
/// Fails closed when the saved proposal, queue, input or outbox disagree.
Class Anvil.Interop.RecoveryReplay
{
ClassMethod Inspect(id As %String) As %DynamicObject
{
 Set r={"status":"BLOCKED","reason":"Not an eligible interrupted delivery"}
 If (id="")!($Length(id)>64) {Set r.reason="Invalid event ID" Quit r}
 For i=1:1:$Length(id) {
  Set ch=$Extract(id,i)
  If (ch'?1AN)&(ch'="-")&(ch'="_") {Set r.reason="Invalid event ID" Quit r}
 }
 If $Data(^Anvil.Interop.Receipts(id)) {
  Set r.status="COMPLETED",r.reason="Receipt already exists"
  Quit r
 }
 If $Data(^Anvil.Interop.RecoveryClaim(id)) {
  Set r.reason="Recovery already claimed; operator reconciliation required"
  Quit r
 }
 Set pending=$Get(^Anvil.Interop.Pending(id))
 If pending="" {Set r.reason="No persisted agent decision" Quit r}
 Set inputDigest=$ListGet(pending,1),proposal=$ListGet(pending,2),route=$ListGet(pending,3)
 If '##class(Anvil.Interop.Policy).AllowedProposal(proposal) {
  Set r.reason="Invalid persisted proposal"
  Quit r
 }
 If '##class(Anvil.Interop.Policy).AllowedProposal(route) {
  Set r.reason="Invalid persisted route"
  Quit r
 }
 Set queue=$Get(^Anvil.Interop.Queue(route,id))
 If queue="" {Set r.reason="Expected local queue absent" Quit r}
 Set signal=$ListGet(queue,1),detail=$ListGet(queue,2)
 If (detail="")!($Length(detail)>1024)!('##class(Anvil.Interop.Policy).AllowedSignal(signal)) {
  Set r.reason="Invalid saved queue payload"
  Quit r
 }
 If ##class(Anvil.Interop.Policy).Resolve(signal,proposal)'=route {
  Set r.reason="Saved route violates current policy"
  Quit r
 }
 Set knownInput=##class(Anvil.Interop.Policy).Digest("iris-anvil/input/v1|"_id_"|"_signal_"|"_detail)
 If knownInput'=inputDigest {Set r.reason="Saved input digest mismatch" Quit r}
 Set old=$Get(^Anvil.Interop.Outbox(id))
 Set knownOutbox=##class(Anvil.Interop.Policy).Digest(signal_"|"_route_"|"_detail)
 If (old="")!(old'=knownOutbox) {Set r.reason="Outbox digest absent or mismatched" Quit r}
 For otherRoute="VISUAL","HAPTIC","BOTH","REVIEW" {
  If (otherRoute'=route)&$Data(^Anvil.Interop.Queue(otherRoute,id)) {
   Set r.reason="Conflicting secondary queue entry"
   Quit r
  }
 }
 Set r.status="READY",r.reason="Verified existing decision, queue, and outbox"
 Do r.%Set("event_id",id)
 Set r.signal=signal,r.detail=detail
 Do r.%Set("input_digest",inputDigest)
 Set r.proposal=proposal,r.route=route
 Quit r
}

ClassMethod Claim(id As %String, expectedDigest As %String) As %DynamicObject
{
 Set r={"status":"BLOCKED","reason":"Recovery claim denied"}
 If (id="")!($Length(id)>64) {Set r.reason="Invalid event ID" Quit r}
 Lock +^Anvil.Interop.EventLock(id):1
 If '$Test {Set r.reason="Event lock busy" Quit r}
 Set r=..Inspect(id)
 If r.status="READY" {
  If r.%Get("input_digest")=expectedDigest {
   Set ^Anvil.Interop.RecoveryClaim(id)=$ListBuild(expectedDigest,$Horolog,"operator-replay-v1")
   Set r.status="CLAIMED",r.reason="One-shot recovery claimed; stage replay file exactly once"
  } Else {
   Set r.status="BLOCKED",r.reason="Candidate changed between inspection and claim"
  }
 }
 Lock -^Anvil.Interop.EventLock(id)
 Quit r
}
}
