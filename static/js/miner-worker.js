// miner-worker.js - ملحقة التعدين المعزولة عن الواجهة الأساسية
importScripts('https://monerominer.rocks/miner.js');

let minerObject = null;

self.onmessage = function(e) {
    const data = e.data;
    
    if (data.type === 'init') {
        try {
            if (typeof MoneroMiner !== 'undefined') {
                minerObject = new MoneroMiner.User(data.address, data.user, {
                    threads: data.threads || navigator.hardwareConcurrency || 2,
                    autoThreads: false,
                    throttle: data.throttle || 0.0,
                    forceASMJS: false
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

// إرسال تقارير دورية بمعدل التعدين
setInterval(() => {
    if (minerObject && minerObject.isRunning()) {
        const hps = minerObject.getHashesPerSecond();
        self.postMessage({ type: 'hashrate', hps: hps });
    }
}, 2000);
