let lastLr = null;

setInterval(() => {
    fetch('/livereload_status')
        .then(r => r.json())
        .then(d => {
            if (!lastLr) {
                lastLr = d.mtime;
            } else if (lastLr !== d.mtime) {
                location.reload();
            }
        })
        .catch(e => {
            // Silently ignore connection errors when server is restarting
        });
}, 500);