/// Demo operation: durable local queue, NOT a real alerting connector.
Class Anvil.Interop.Deliver Extends Ens.BusinessOperation
{
Method OnMessage(pRequest As Anvil.Interop.Dispatch, Output pResponse As Anvil.Interop.Result) As %Status
{
 Set pResponse=##class(Anvil.Interop.Result).%New()
 Set pResponse.EventId=pRequest.EventId,pResponse.Route=pRequest.Route
 Set expected="Anvil."_pRequest.Route
 If (..%ConfigName'=expected) {
  Set pResponse.State="BLOCKED",pResponse.Reason="Operation/route mismatch"
  Quit $$$OK
 }
 Lock +^Anvil.Interop.OutboxLock(pRequest.EventId):5
 If '$Test {
  Set pResponse.State="BLOCKED",pResponse.Reason="Queue lock timeout"
  Quit $$$OK
 }
 Try {
  Set canonical=pRequest.Signal_"|"_pRequest.Route_"|"_pRequest.Detail
  Set digest=##class(Anvil.Interop.Policy).Digest(canonical)
  Set old=$Get(^Anvil.Interop.Outbox(pRequest.EventId))
  If (old'="")&(old'=digest) {
   Set pResponse.State="BLOCKED",pResponse.Reason="Conflicting event-id replay"
  } Else {
   Set ^Anvil.Interop.Outbox(pRequest.EventId)=digest
   Set ^Anvil.Interop.Queue(pRequest.Route,pRequest.EventId)=$ListBuild(pRequest.Signal,pRequest.Detail,$Horolog)
   Set pResponse.State="QUEUED",pResponse.Reason="Recorded in local demo outbox"
  }
 } Catch ex {
  Set pResponse.State="BLOCKED",pResponse.Reason="Local queue write failed"
 }
 Lock -^Anvil.Interop.OutboxLock(pRequest.EventId)
 Quit $$$OK
}
}
