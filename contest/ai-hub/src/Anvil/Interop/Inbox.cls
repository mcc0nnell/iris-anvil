/// IRIS File Inbound Adapter accepts small synthetic JSON event files.
Class Anvil.Interop.Inbox Extends Ens.BusinessService
{
Parameter ADAPTER = "EnsLib.File.InboundAdapter";

Method OnProcessInput(pInput As %FileCharacterStream, Output pOutput As %RegisteredObject) As %Status
{
 Set raw=""
 While 'pInput.AtEnd {
  Set raw=raw_pInput.Read(1024)
  If $Length(raw)>2048 Quit
 }
 If $Length(raw)>2048 Quit $$$ERROR($$$GeneralError,"Alert exceeds demo input limit")
 Set sc=$$$OK
 Try {
  Set payload=##class(%DynamicObject).%FromJSON(raw)
  Set req=##class(Anvil.Interop.Alert).%New()
  Set req.EventId=payload.%Get("event_id","")
  Set req.Signal=payload.%Get("signal","")
  Set req.Detail=payload.%Get("detail","")
 } Catch ex {
  Set sc=$$$ERROR($$$GeneralError,"Invalid alert JSON")
 }
 If '$SYSTEM.Status.IsOK(sc) Quit sc
 Set sc=..SendRequestSync("Anvil.Router",req,.response,20)
 Set pOutput=response
 Quit sc
}
}
