
// content.js
(function() {
	/** YouTube decorates the player <div> with .ad-showing while an ad runs */
	const player = document.querySelector('.html5-video-player');

	if (!player) return; // safety in case the selector changes

	const report = () => {
		chrome.runtime.sendMessage({
			type: 'AD_STATUS',
			adActive: player.classList.contains('ad-showing')
		});
	};

	// Send one message right away
	report();

	// Watch for class changes
	new MutationObserver(report).observe(player, {
		attributes: true,
		attributeFilter: ['class']
	});

	// Optional: make sure we re-report after each play / ended
	player
		.querySelector('video')
		?.addEventListener('play', report, { passive: true });
})();
