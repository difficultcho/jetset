const api = require('../../utils/api.js');
const { toastError } = require('../../utils/request.js');

Page({
  data: { logs: [], balance: 0, loaded: false },

  async onShow() {
    try {
      const [me, logs] = await Promise.all([api.me(), api.pointsLogs()]);
      this.setData({
        balance: me.points,
        loaded: true,
        logs: logs.map((r) => ({
          id: r.id,
          change: r.change,
          plus: r.change > 0,
          reason: r.reason,
          remark: r.remark,
          balance: r.balance_after,
          time: String(r.created_at).replace('T', ' ').slice(0, 16)
        }))
      });
    } catch (e) {
      toastError(e);
    }
  }
});
