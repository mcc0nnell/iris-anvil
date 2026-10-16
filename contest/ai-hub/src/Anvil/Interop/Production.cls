/// Synthetic accessibility incident routing through real IRIS interoperability hosts.
Class Anvil.Interop.Production Extends Ens.Production
{
XData ProductionDefinition
{
<Production Name="Anvil.Interop.Production" LogGeneralTraceEvents="true">
<Description>AI Hub proposed routing with fail-closed policy and local demo queues</Description>
<ActorPoolSize>2</ActorPoolSize>
<Item Name="Anvil.Inbox" Category="" ClassName="Anvil.Interop.Inbox" PoolSize="1" Enabled="true" Foreground="false">
<Setting Target="Adapter" Name="FilePath">/opt/iris-anvil/inbox</Setting>
<Setting Target="Adapter" Name="FileSpec">*.json</Setting>
<Setting Target="Adapter" Name="CallInterval">2</Setting>
<Setting Target="Adapter" Name="ArchivePath">/opt/iris-anvil/archive</Setting>
</Item>
<Item Name="Anvil.Router" Category="" ClassName="Anvil.Interop.Router" PoolSize="1" Enabled="true" Foreground="false"/>
<Item Name="Anvil.VISUAL" Category="" ClassName="Anvil.Interop.Deliver" PoolSize="1" Enabled="true" Foreground="false"/>
<Item Name="Anvil.HAPTIC" Category="" ClassName="Anvil.Interop.Deliver" PoolSize="1" Enabled="true" Foreground="false"/>
<Item Name="Anvil.BOTH" Category="" ClassName="Anvil.Interop.Deliver" PoolSize="1" Enabled="true" Foreground="false"/>
<Item Name="Anvil.REVIEW" Category="" ClassName="Anvil.Interop.Deliver" PoolSize="1" Enabled="true" Foreground="false"/>
</Production>
}
}
