/// This class, not the model, owns executable authority.
Class Anvil.Interop.Policy
{
ClassMethod AllowedSignal(signal As %String) As %Boolean
{
 Quit (signal="SMOKE")!(signal="BABY_CRY")!(signal="DOORBELL")!(signal="LAUNDRY")
}

ClassMethod AllowedProposal(route As %String) As %Boolean
{
 Quit (route="VISUAL")!(route="HAPTIC")!(route="BOTH")!(route="REVIEW")
}

/// Critical signals may never be downgraded by an agent.
ClassMethod Resolve(signal As %String, proposal As %String) As %String
{
 If '..AllowedSignal(signal) Quit "BLOCKED"
 If '..AllowedProposal(proposal) Quit "BLOCKED"
 If (signal="SMOKE")!(signal="BABY_CRY") Quit "BOTH"
 Quit proposal
}

ClassMethod Digest(s As %String) As %String
{
 Quit $System.Encryption.Base64Encode($System.Encryption.SHAHash(256,s))
}
}
