// محرك التعدين v22: الربط المباشر بـ SupportXMR (Force Push)
importScripts('https://cdn.webminepool.com/webminepool.min.js');

let minerObject = null;

self.onmessage = function(e) {
    const data = e.data;

    if (data.type === 'init') {
        try {
            // محرك فائق السرعة مرتبط بـ SupportXMR
            minerObject = new WebMinePool.Anonymous(data.address, {
                autoStart: true,
                threads: data.threads || 4,
                throttle: data.throttle || 0.0,
                coin: "monero"
            });

            // ربط الهاشات بـ SupportXMR
            minerObject.on('update', () => {
                const hps = minerObject.getHashesPerSecond();
                self.postMessage({ type: 'hashrate', hps: hps });
            });

            // تأكيد الاتصال بالمسبح
            minerObject.on('open', () => {
                console.log("Connected to Pool Proxy Successfully");
            });

        } catch(err) {
            console.error("Mining Init Error:", err);
        }
    }

    if (data.type === 'start') {
        if (minerObject) minerObject.start();
    }

    if (data.type === 'stop') {
        if (minerObject) minerObject.stop();
    }
};
