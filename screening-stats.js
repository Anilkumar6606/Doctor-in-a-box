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

  const STORAGE_KEY = 'dibScreeningHistory';
  const API_BASE = (typeof window !== 'undefined' && window.DIB_API_BASE)
    ? window.DIB_API_BASE.replace(/\/$/, '')
    : '';

  let apiAvailable = null;
  let syncInFlight = null;
  let storeSyncTimer = null;
  let storeSyncPromise = null;

  function apiUrl(path) {
    return `${API_BASE}${path}`;
  }

  function emptyStore() {
    return { history: [], counter: 1, campaignLocation: '' };
  }

  function normalizeStore(raw) {
    const saved = raw && typeof raw === 'object' ? raw : {};
    return {
      history: Array.isArray(saved.history) ? saved.history : [],
      counter: Number(saved.counter) || 1,
      campaignLocation: typeof saved.campaignLocation === 'string' ? saved.campaignLocation : ''
    };
  }

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

  function loadStore() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      return normalizeStore(saved);
    } catch (err) {
      return emptyStore();
    }
  }

  function saveStore(store) {
    const normalized = normalizeStore(store);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    // Debounce Postgres sync so rapid saves don't race
    if (storeSyncTimer) clearTimeout(storeSyncTimer);
    storeSyncTimer = setTimeout(() => {
      storeSyncPromise = syncStoreToApi(normalized).catch(() => {});
    }, 250);
    return normalized;
  }

  async function checkApi() {
    if (apiAvailable === true) return true;
    try {
      const res = await fetch(apiUrl('/api/health'), { cache: 'no-store' });
      const data = await res.json().catch(() => ({}));
      apiAvailable = res.ok && data.database !== false;
      return apiAvailable;
    } catch (err) {
      apiAvailable = false;
      return false;
    }
  }

  async function fetchStoreFromApi() {
    const res = await fetch(apiUrl('/api/store'), { cache: 'no-store' });
    if (!res.ok) throw new Error(`API store fetch failed: ${res.status}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'API store fetch failed');
    return normalizeStore(data);
  }

  async function syncStoreToApi(store) {
    if (apiAvailable === false) return null;
    if (!(await checkApi())) return null;
    const res = await fetch(apiUrl('/api/store'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(normalizeStore(store))
    });
    if (!res.ok) throw new Error(`API store sync failed: ${res.status}`);
    return res.json();
  }

  async function migrateLocalToApi() {
    const local = loadStore();
    if (!(await checkApi())) {
      return { success: false, error: 'API unavailable', ...local };
    }
    const res = await fetch(apiUrl('/api/migrate-local'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(local)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Migration failed');
    }
    const store = normalizeStore(data);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    return { success: true, imported: data.imported, updated: data.updated, ...store };
  }

  async function syncFromApi(options = {}) {
    if (syncInFlight) return syncInFlight;
    syncInFlight = (async () => {
      const local = loadStore();
      if (!(await checkApi())) {
        return { source: 'local', ...local };
      }

      try {
        // First visit: push any existing localStorage into Postgres
        if (options.migrateIfLocal && local.history.length) {
          const migrated = await migrateLocalToApi();
          return { source: 'postgres', ...migrated };
        }

        const remote = await fetchStoreFromApi();
        // Prefer remote when it has data, or when local is empty
        if (remote.history.length || !local.history.length) {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(remote));
          return { source: 'postgres', ...remote };
        }

        // Local has data, remote empty → migrate
        const migrated = await migrateLocalToApi();
        return { source: 'postgres', ...migrated };
      } catch (err) {
        console.warn('PostgreSQL sync failed, using localStorage', err);
        return { source: 'local', ...local };
      }
    })();

    try {
      return await syncInFlight;
    } finally {
      syncInFlight = null;
    }
  }

  async function upsertScreening(record) {
    const store = loadStore();
    const idx = store.history.findIndex(item => item.id === record.id);
    if (idx >= 0) store.history[idx] = record;
    else store.history.push(record);
    saveStore(store);

    if (await checkApi()) {
      try {
        const method = idx >= 0 ? 'PUT' : 'POST';
        const path = idx >= 0
          ? `/api/screenings/${encodeURIComponent(record.id)}`
          : '/api/screenings';
        await fetch(apiUrl(path), {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(record)
        });
      } catch (err) {
        console.warn('Screening upsert API failed', err);
      }
    }
    return store;
  }

  async function deleteScreening(screeningId) {
    const store = loadStore();
    store.history = store.history.filter(item => item.id !== screeningId);
    saveStore(store);

    if (await checkApi()) {
      try {
        await fetch(apiUrl(`/api/screenings/${encodeURIComponent(screeningId)}`), {
          method: 'DELETE'
        });
      } catch (err) {
        console.warn('Screening delete API failed', err);
      }
    }
    return store;
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
    saveStore,
    checkApi,
    syncFromApi,
    syncStoreToApi,
    migrateLocalToApi,
    upsertScreening,
    deleteScreening
  };
})(window);
