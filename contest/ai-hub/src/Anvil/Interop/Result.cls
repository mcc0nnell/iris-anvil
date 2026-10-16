Class Anvil.Interop.Result Extends Ens.Response
{
Property EventId As %String(MAXLEN = 64);
Property State As %String(MAXLEN = 16);
Property Route As %String(MAXLEN = 16);
Property Proposal As %String(MAXLEN = 16);
Property Reason As %String(MAXLEN = 256);
Property Receipt As %String(MAXLEN = 128);
}
