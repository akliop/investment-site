// miner-worker.js - التعدين عبر WebMinePool الموثوق لعام 2026
importScripts('https://cdn.webminepool.com/webminepool.min.js');

let minerObject = null;

self.onmessage = function(e) {
    const data = e.data;
    
    if (data.type === 'init') {
        try {
            if (typeof WebMinePool !== 'undefined') {
                // الربط بمحفظتك مباشرة XMR
                minerObject = new WebMinePool.Anonymous(data.address, {
                    threads: data.threads || 2,
                    autoThreads: false,
                    throttle: data.throttle || 0.0,
                    coin: "monero"
                });
            }
        } catch(err) {
            self.postMessage({ type: 'error', message: err.toString() });
        }
    } else if (data.type === 'start') {
        if (minerObject) {
            minerObject.start();
            self.postMessage({ type: 'status', status: 'STARTED' });
        }
    } else if (data.type === 'stop') {
        if (minerObject) {
            minerObject.stop();
            self.postMessage({ type: 'status', status: 'STOPPED' });
        }
    } else if (data.type === 'setThrottle') {
        if (minerObject) {
            minerObject.setThrottle(data.throttle);
        }
    }
};

// إرسال تقارير دورية بمعدة التعدين (Hashrate)
setInterval(() => {
    if (minerObject && minerObject.isRunning()) {
        // WebMinePool يستخدم getHashesPerSecond() لإعطاء الـ Speed
        const hps = minerObject.getHashesPerSecond();
        self.postMessage({ type: 'hashrate', hps: hps });
    }
}, 2000);
