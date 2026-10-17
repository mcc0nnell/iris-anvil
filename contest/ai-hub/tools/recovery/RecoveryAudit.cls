/// Read-only snapshot of IRIS Anvil demo outbox/receipt inconsistencies.
/// Operator diagnostic only; never dispatches, repairs, or deletes event data.
Class Anvil.Interop.RecoveryAudit
{
ClassMethod Run()
{
 Write "ANVIL_RECOVERY_AUDIT_BEGIN",!
 Set pendingCount=0,orphanCount=0,brokenCount=0,completedCount=0
 Set id=""
 For {
  Set id=$Order(^Anvil.Interop.Pending(id))
  Quit:id=""
  Set pendingCount=pendingCount+1
  If $Data(^Anvil.Interop.Receipts(id)) {
   Set brokenCount=brokenCount+1
   Write "AUDIT|PENDING_WITH_RECEIPT|",id,!
  } ElseIf $Data(^Anvil.Interop.Outbox(id)) {
   Write "AUDIT|PENDING_WITH_OUTBOX|",id,!
  } Else {
   Write "AUDIT|PENDING_BEFORE_DELIVERY|",id,!
  }
 }
 Set id=""
 For {
  Set id=$Order(^Anvil.Interop.Outbox(id))
  Quit:id=""
  If '$Data(^Anvil.Interop.Pending(id)) {
   If '$Data(^Anvil.Interop.Receipts(id)) {
    Set orphanCount=orphanCount+1
    Write "AUDIT|ORPHAN_OUTBOX|",id,!
   } Else {
    Set rec=^Anvil.Interop.Receipts(id),route=$ListGet(rec,4)
    If (route="")!('$Data(^Anvil.Interop.Queue(route,id))) {
     Set brokenCount=brokenCount+1
     Write "AUDIT|RECEIPT_WITHOUT_QUEUE|",id,!
    } Else {
     Set completedCount=completedCount+1
     Write "AUDIT|COMPLETED|",id,"|",route,!
    }
   }
  }
 }
 Set id=""
 For {
  Set id=$Order(^Anvil.Interop.Receipts(id))
  Quit:id=""
  If ('$Data(^Anvil.Interop.Outbox(id)))&('$Data(^Anvil.Interop.Pending(id))) {
   Set brokenCount=brokenCount+1
   Write "AUDIT|RECEIPT_WITHOUT_OUTBOX|",id,!
  }
 }
 Write "ANVIL_RECOVERY_AUDIT_SUMMARY|pending=",pendingCount,"|orphan=",orphanCount,"|broken=",brokenCount,"|completed=",completedCount,!
 Write "ANVIL_RECOVERY_AUDIT_END",!
}
}
