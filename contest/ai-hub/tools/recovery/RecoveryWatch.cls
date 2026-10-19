/// Optional read-only safety gate before any operator-assisted or armed replay.
/// Requires stale queue state AND an IRIS failed Alert message for the same event.
Class Anvil.Interop.RecoveryWatch
{
ClassMethod Probe(id As %String, minimumAge As %Integer = 120) As %DynamicObject
{
 Set r={"status":"BLOCKED","reason":"Recovery watch not eligible"}
 If (minimumAge<60)!(minimumAge>86400) {Set r.reason="Invalid minimum age" Quit r}
 Set productionName=""
 Set running=##class(Ens.Director).IsProductionRunning(.productionName)
 If ('running)!(productionName'="Anvil.Interop.Production") {
  Set r.reason="Expected IRIS production is not running"
  Quit r
 }
 Set plan=##class(Anvil.Interop.RecoveryReplay).Inspect(id)
 If plan.status'="READY" {Set r.reason=plan.reason Quit r}
 Set q=$Get(^Anvil.Interop.Queue(plan.route,id))
 Set created=$ListGet(q,3)
 If (created="")!($Length(created,",")'=2) {Set r.reason="Queue timestamp missing" Quit r}
 Set age=($Piece($Horolog,",",1)-$Piece(created,",",1))*86400+$Piece($Horolog,",",2)-$Piece(created,",",2)
 If (age<minimumAge)!(age<0) {Set r.reason="Queue below minimum age" Quit r}
 Set st=##class(%SQL.Statement).%New()
 Set sc=st.%Prepare("SELECT TOP 250 MessageBodyId FROM Ens.MessageHeader WHERE MessageBodyClassName = 'Anvil.Interop.Alert' AND Status = 5 ORDER BY ID DESC")
 If '$System.Status.IsOK(sc) {Set r.reason="IRIS failed-message query unavailable" Quit r}
 Set rows=st.%Execute()
 If '$IsObject(rows) {Set r.reason="IRIS failed-message query failed" Quit r}
 Set found=0
 While rows.%Next() {
  Set obj=##class(Anvil.Interop.Alert).%OpenId(rows.%Get("MessageBodyId"))
  If $IsObject(obj) {
   If obj.EventId=id {Set found=1 Quit}
  }
 }
 If 'found {Set r.reason="No matching failed IRIS Alert in last 250 headers" Quit r}
 Set r.status="READY",r.reason="Stale queue and matching failed IRIS Alert confirmed"
 Do r.%Set("event_id",id)
 Do r.%Set("input_digest",plan.%Get("input_digest"))
 Set r.route=plan.route,r.signal=plan.signal
 Do r.%Set("age_seconds",age)
 Quit r
}
}
