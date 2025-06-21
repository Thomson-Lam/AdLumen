
// background.js (Manifest V3 service worker)
let adActive = false;

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
	if (msg.type === 'AD_STATUS') {
		adActive = msg.adActive;          // update cache
		/** forward to any open popups so they update live */
		chrome.runtime.sendMessage({ type: 'AD_STATUS_BROADCAST', adActive });
		return;
	}
	if (msg.type === 'QUERY_AD_STATUS') {
		reply({ adActive });              // synchronous answer to popup
	}
});
