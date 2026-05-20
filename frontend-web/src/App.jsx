import { useAgentStream } from './hooks/useAgentStream'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import AgentTrace from './components/AgentTrace'
import styles from './App.module.css'

export default function App() {
  const {
    events, messages, isStreaming, sessionId,
    provider, setProvider,
    apiKey, setApiKey,
    providerChanged,
    sendMessage, indexDocs, newSession, stop
  } = useAgentStream()

  return (
    <div className={styles.layout}>
      <Sidebar
        provider={provider}
        setProvider={setProvider}
        apiKey={apiKey}
        setApiKey={setApiKey}
        sessionId={sessionId}
        onIndex={indexDocs}
        providerChanged={providerChanged}
      />
      <div className={styles.chat}>
        <ChatPanel
          messages={messages}
          isStreaming={isStreaming}
          onSend={sendMessage}
          onNew={newSession}
          stop={stop}
        />
      </div>
      <div className={styles.trace}>
        <AgentTrace events={events} isStreaming={isStreaming} />
      </div>
    </div>
  )
}
