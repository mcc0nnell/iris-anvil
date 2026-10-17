/// IRIS interoperability Business Process: real AI Hub -> policy -> operation.
/// Event ID locks protect immutable receipts and prevent duplicate dispatch.
Class Anvil.Interop.Router Extends Ens.BusinessProcess
{
Method OnRequest(pRequest As Anvil.Interop.Alert, Output pResponse As Anvil.Interop.Result) As %Status
{
 Set pResponse=##class(Anvil.Interop.Result).%New()
 Set pResponse.EventId=pRequest.EventId,pResponse.State="BLOCKED"
 Set signal=$ZConvert(pRequest.Signal,"U")
 If (pRequest.EventId="")!($Length(pRequest.EventId)>64)!($Length(pRequest.Detail)>1024) {
  Set pResponse.Reason="Invalid event identifier or payload size"
  Quit $$$OK
 }
 For i=1:1:$Length(pRequest.EventId) {
  Set c=$Extract(pRequest.EventId,i)
  If (c'?1AN)&(c'="-")&(c'="_") {
   Set pResponse.Reason="Event identifier must be alphanumeric, dash, or underscore"
   Quit $$$OK
  }
 }
 If '##class(Anvil.Interop.Policy).AllowedSignal(signal) {
  Set pResponse.Reason="Signal outside allowlist"
  Quit $$$OK
 }
 Lock +^Anvil.Interop.EventLock(pRequest.EventId):30
 If '$Test {
  Set pResponse.Reason="Event lock timeout"
  Quit $$$OK
 }
 Try {
  Set sc=..ProcessLocked(pRequest,signal,.pResponse)
 } Catch ex {
  Set pResponse.State="BLOCKED",pResponse.Reason="Interop workflow exception"
  Set sc=$$$OK
 }
 Lock -^Anvil.Interop.EventLock(pRequest.EventId)
 Quit sc
}

Method ProcessLocked(pRequest As Anvil.Interop.Alert, signal As %String, Output pResponse As Anvil.Interop.Result) As %Status
{
 Set pResponse=##class(Anvil.Interop.Result).%New()
 Set pResponse.EventId=pRequest.EventId,pResponse.State="BLOCKED"
 Set inputDigest=##class(Anvil.Interop.Policy).Digest("iris-anvil/input/v1|"_pRequest.EventId_"|"_signal_"|"_pRequest.Detail)
 Set old=$Get(^Anvil.Interop.Receipts(pRequest.EventId))
 If old'="" {
  If $ListGet(old,1)'=inputDigest {
   Set pResponse.Reason="Event ID reused with different payload"
  } Else {
   Set pResponse.Proposal=$ListGet(old,3),pResponse.Route=$ListGet(old,4)
   Set pResponse.Receipt=$ListGet(old,5),pResponse.State="QUEUED"
   Set pResponse.Reason="Idempotent replay; no second agent call or delivery"
  }
  Quit $$$OK
 }
 // Persist the agent proposal *before* forwarding the operation, so a
 // crash after queue acknowledgement cannot force a fresh model decision.
 Set pending=$Get(^Anvil.Interop.Pending(pRequest.EventId))
 If pending'="" {
  If $ListGet(pending,1)'=inputDigest {
   Set pResponse.Reason="Pending event ID reused with different payload"
   Quit $$$OK
  }
  Set savedProposal=$ListGet(pending,2),route=$ListGet(pending,3)
  If ('##class(Anvil.Interop.Policy).AllowedProposal(savedProposal))!(##class(Anvil.Interop.Policy).Resolve(signal,savedProposal)'=route) {
   Set pResponse.Reason="Invalid pending decision requires reconciliation"
   Quit $$$OK
  }
  Set proposal={"route": (savedProposal), "reason":"Recovered previously persisted agent proposal"}
 } Else {
  // An orphaned outbox from an older run has no trustworthy proposal.
  // Never improvise another agent answer to repair it.
  If $Get(^Anvil.Interop.Outbox(pRequest.EventId))'="" {
   Set pResponse.Reason="Outbox without pending decision requires reconciliation"
   Quit $$$OK
  }
  Set proposal=##class(Anvil.Interop.Agent).Propose(signal,pRequest.Detail)
  Set route=##class(Anvil.Interop.Policy).Resolve(signal,proposal.route)
  If route="BLOCKED" {
   Set pResponse.Proposal=proposal.route,pResponse.Reason=proposal.reason
   Quit $$$OK
  }
  Set ^Anvil.Interop.Pending(pRequest.EventId)=$ListBuild(inputDigest,proposal.route,route)
 }
 Set pResponse.Proposal=proposal.route
 Set outgoing=##class(Anvil.Interop.Dispatch).%New()
 Set outgoing.EventId=pRequest.EventId,outgoing.Signal=signal,outgoing.Route=route,outgoing.Detail=pRequest.Detail
 Set sc=..SendRequestSync("Anvil."_route,outgoing,.delivery,15)
 If '$System.Status.IsOK(sc) {
  Set pResponse.Reason="Interoperability operation error"
  Quit sc
 }
 If '$IsObject(delivery) {
  Set pResponse.Reason="Missing operation acknowledgement"
  Quit $$$OK
 }
 If delivery.State'="QUEUED" {
  Set pResponse.Reason=delivery.Reason
  Quit $$$OK
 }
 Set canonical="iris-anvil/interop/v1|"_inputDigest_"|"_proposal.route_"|"_route
 Set receipt=##class(Anvil.Interop.Policy).Digest(canonical)
 Set ^Anvil.Interop.Receipts(pRequest.EventId)=$ListBuild(inputDigest,signal,proposal.route,route,receipt,$Horolog)
 Kill ^Anvil.Interop.Pending(pRequest.EventId)
 Set pResponse.State="QUEUED",pResponse.Route=route,pResponse.Receipt=receipt,pResponse.Reason="AI decision independently governed and demo queue acknowledged"
 Quit $$$OK
}
}
