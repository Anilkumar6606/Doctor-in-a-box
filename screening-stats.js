(function (global) {
  const CHECKUPS = [
    { id: 'bp', label: 'Blood Pressure', price: 0 },
    { id: 'sugar', label: 'Blood Sugar', price: 50 },
    { id: 'oximetry', label: 'Oximetry (SpO₂)', price: 50 },
    { id: 'lipid', label: 'Complete Cholesterol / 5-in-1 Lipid Profile', price: 349 },
    { id: 'bmi', label: 'BMI', price: 0, packageOnly: true },
    { id: 'height', label: 'Height', price: 0, packageOnly: true },
    { id: 'weight', label: 'Weight', price: 0, packageOnly: true },
    { id: 'temp', label: 'Body Temperature', price: 0, packageOnly: true },
    { id: 'bloodgroup', label: 'Blood Group', price: 50 }
  ];

  function getLocalDateIso(date = new Date()) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  function getCheckup(id) {
    return CHECKUPS.find(item => item.id === id) || { id, label: id, price: 0 };
  }

  function getCheckupPrice(id) {
    return Number(getCheckup(id).price || 0);
  }

  function getScreeningDate(record) {
    if (record?.person?.date) return record.person.date;
    const created = String(record?.createdAt || '');
    return created.length >= 10 ? created.slice(0, 10) : '';
  }

  function selectedTestIds(record) {
    if (Array.isArray(record?.tests) && record.tests.length) {
      return record.tests.map(test => test.id).filter(Boolean);
    }
    return Object.keys(record?.checkups || {}).filter(id => record.checkups[id]);
  }

  function getTestEntries(record) {
    if (Array.isArray(record?.tests) && record.tests.length) {
      return record.tests.map(test => ({
        id: test.id,
        price: Number.isFinite(Number(test.price)) ? Number(test.price) : getCheckupPrice(test.id)
      }));
    }
    return selectedTestIds(record).map(id => ({
      id,
      price: getCheckupPrice(id)
    }));
  }

  function getRecordAmount(record) {
    const entries = getTestEntries(record);
    if (entries.length) {
      return entries.reduce((sum, test) => sum + test.price, 0);
    }
    const stored = Number(record?.amount);
    return Number.isFinite(stored) ? stored : 0;
  }

  function normalizePayment(method) {
    const value = String(method || '').trim().toLowerCase();
    if (value === 'online') return 'online';
    if (value === 'cash') return 'cash';
    return 'unpaid';
  }

  function matchesCampaign(record, campaign) {
    if (!campaign) return true;
    return (record?.person?.camp || '').trim() === campaign.trim();
  }

  function createEmptyStats() {
    return {
      todayScreenings: 0,
      totalScreenings: 0,
      todayCheckups: 0,
      totalCheckups: 0,
      freeCheckups: 0,
      paidCheckups: 0,
      onlineAmount: 0,
      cashAmount: 0,
      unpaidAmount: 0,
      totalAmount: 0,
      todayAmount: 0,
      todayOnlineAmount: 0,
      todayCashAmount: 0,
      todayFreeCheckups: 0,
      todayPaidCheckups: 0
    };
  }

  function computeStats(history, options = {}) {
    const stats = createEmptyStats();
    const today = options.today || getLocalDateIso();
    const campaign = (options.campaign || '').trim();
    const list = Array.isArray(history) ? history : [];

    list.forEach(record => {
      if (!matchesCampaign(record, campaign)) return;

      const entries = getTestEntries(record);
      const amount = getRecordAmount(record);
      const date = getScreeningDate(record);
      const isToday = date === today;
      const payment = normalizePayment(record.person?.paymentMethod);

      stats.totalScreenings += 1;
      stats.totalCheckups += entries.length;
      stats.totalAmount += amount;

      entries.forEach(test => {
        if (test.price > 0) stats.paidCheckups += 1;
        else stats.freeCheckups += 1;
      });

      if (payment === 'online') stats.onlineAmount += amount;
      else if (payment === 'cash') stats.cashAmount += amount;
      else stats.unpaidAmount += amount;

      if (isToday) {
        stats.todayScreenings += 1;
        stats.todayCheckups += entries.length;
        stats.todayAmount += amount;
        if (payment === 'online') stats.todayOnlineAmount += amount;
        else if (payment === 'cash') stats.todayCashAmount += amount;
        entries.forEach(test => {
          if (test.price > 0) stats.todayPaidCheckups += 1;
          else stats.todayFreeCheckups += 1;
        });
      }
    });

    return stats;
  }

  function computeDayStats(history, date, campaign = '') {
    const stats = createEmptyStats();
    const list = Array.isArray(history) ? history : [];

    list.forEach(record => {
      if (!matchesCampaign(record, campaign)) return;
      if (getScreeningDate(record) !== date) return;

      const entries = getTestEntries(record);
      const amount = getRecordAmount(record);
      const payment = normalizePayment(record.person?.paymentMethod);

      stats.todayScreenings += 1;
      stats.todayCheckups += entries.length;
      stats.todayAmount += amount;
      if (payment === 'online') stats.todayOnlineAmount += amount;
      else if (payment === 'cash') stats.todayCashAmount += amount;

      entries.forEach(test => {
        if (test.price > 0) stats.todayPaidCheckups += 1;
        else stats.todayFreeCheckups += 1;
      });
    });

    return stats;
  }

  function formatMoney(value) {
    return `₹ ${Math.round(Number(value) || 0).toLocaleString('en-IN')}`;
  }

  const STORAGE_KEY = 'dibScreeningHistory';

  function loadStore() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      return {
        history: Array.isArray(saved.history) ? saved.history : [],
        counter: Number(saved.counter) || 1,
        campaignLocation: typeof saved.campaignLocation === 'string' ? saved.campaignLocation : ''
      };
    } catch (err) {
      return { history: [], counter: 1, campaignLocation: '' };
    }
  }

  function saveStore(store) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      history: store.history || [],
      counter: store.counter || 1,
      campaignLocation: store.campaignLocation || ''
    }));
  }

  global.ScreeningStats = {
    CHECKUPS,
    STORAGE_KEY,
    getLocalDateIso,
    getScreeningDate,
    getCheckup,
    getCheckupPrice,
    selectedTestIds,
    getTestEntries,
    getRecordAmount,
    normalizePayment,
    computeStats,
    computeDayStats,
    formatMoney,
    loadStore,
    saveStore
  };
})(window);
