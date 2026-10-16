/// The AI Hub agent proposes a route; it cannot deliver an alert or modify policy.
Class Anvil.Interop.Agent
{
ClassMethod Propose(signal As %String, detail As %String) As %DynamicObject
{
 Set result={"route":"UNAVAILABLE","reason":"AI Hub has not returned a valid decision"}
 Set key=$System.Util.GetEnviron("OPENAI_API_KEY")
 If key="" {
  Set result.reason="OPENAI_API_KEY missing; no agent decision made"
  Quit result
 }
 Try {
  Set provider=##class(%AI.Provider).Create("openai", {"api_key": (key)})
  Set agent=##class(%AI.Agent).%New(provider)
  Set agent.Model="gpt-4o-mini"
  Set agent.SystemPrompt="You are an alert interoperability router. Output exactly one token: VISUAL, HAPTIC, BOTH or REVIEW. Consider the type and detail. SMOKE and BABY_CRY should receive BOTH. Unknown or ambiguous cases should receive REVIEW. Do not include punctuation or explanations. You only propose: independent policy decides execution."
  Set session=agent.CreateSession()
  Set response=agent.Chat(session,"Signal: "_signal_$Char(10)_"Detail: "_detail)
  Set candidate=$ZConvert($ZStrip(response.Content,"<>W"),"U")
  If ##class(Anvil.Interop.Policy).AllowedProposal(candidate) {
   Set result.route=candidate,result.reason="AI Hub returned an allowlisted proposal"
  } Else {
   Set result.reason="AI Hub returned an invalid or noncanonical proposal"
  }
 } Catch ex {
  Set result.reason="AI Hub provider/agent invocation failed"
 }
 Quit result
}
}
