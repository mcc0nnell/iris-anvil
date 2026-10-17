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
 Set providerSettings={"api_key":(key)}
 // Optional explicitly configured OpenAI-compatible inference endpoint.
 // Never permit cleartext remote traffic carrying a provider credential.
 Set baseURL=$System.Util.GetEnviron("AI_HUB_OPENAI_BASE_URL")
 If baseURL'="" {
  Set loopback=($Extract(baseURL,1,$Length("http://127.0.0.1:"))="http://127.0.0.1:")
  Set tls=($Extract(baseURL,1,8)="https://")
  If ('loopback)&('tls) {
   Set result.reason="Configured provider endpoint must use HTTPS or local loopback"
   Quit result
  }
  // Build 154 joins relative API paths: the slash avoids replacing /v1.
  If $Extract(baseURL,$Length(baseURL))'="/" {
   Set result.reason="Configured provider endpoint must end with a slash"
   Quit result
  }
  Do providerSettings.%Set("base_url",baseURL)
 }
 Try {
  Set provider=##class(%AI.Provider).Create("openai",providerSettings)
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
