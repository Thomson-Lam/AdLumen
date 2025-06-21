import { useState, useEffect } from 'react';
import './App.css';

// Define the type of messages exchanged
type Message =
| { type: "AD_STATUS"; adActive: boolean }
| { type: "QUERY_AD_STATUS" }
| { type: "AD_STATUS_BROADCAST"; adActive: boolean };

// If you want to be extra strict, you can also type the response to QUERY_AD_STATUS:
type QueryAdStatusResponse = { adActive: boolean };

function App() {
const [isAd, setIsAd] = useState(false);

useEffect(() => {
// Ask once when the popup opens
chrome.runtime.sendMessage(
{ type: "QUERY_AD_STATUS" } as Message,
(resp: QueryAdStatusResponse | undefined) => {
setIsAd(resp?.adActive ?? false);
}
);

// Listen for live broadcasts
const listener = (msg: Message) => {
if (msg.type === "AD_STATUS_BROADCAST") {
setIsAd(msg.adActive);
}
};

chrome.runtime.onMessage.addListener(listener);
return () => chrome.runtime.onMessage.removeListener(listener);
}, []);

return (
<div style={{ fontSize: 16, minWidth: 140, padding: 12 }}>
    {isAd ? "🔴 Ad is playing" : "🟢 No ad detected"}
</div>
);
}

export default App;
