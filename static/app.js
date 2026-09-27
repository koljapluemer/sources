// @ts-check
/**
 * @typedef {{family?: string, given?: string, prefix?: string, suffix?: string}} Name
 * @typedef {{type: 'literal'|'text'|'integer'|'range'|'name'|'list'|'date'|'uri'|'verbatim'|'key', choices?: string[]}} FieldDef
 * @typedef {{fields: Record<string, FieldDef>, entryTypes: Record<string, string[]>, nameParts: string[]}} Schema
 * @typedef {{key: string, entrytype: string, title?: string, aliases?: string[], extra?: Record<string, string>, [field: string]: any}} Source
 */

// @ts-ignore globals from CDN
const { createApp, ref, computed, onMounted, watch, h } = Vue;
// @ts-ignore
const lucide_ = lucide;

/**
 * @param {string} method
 * @param {string} url
 * @param {any} [body]
 */
async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

const go = (/** @type {string} */ hash) => { location.hash = hash; };

const Icon = {
  props: { name: { type: String, required: true }, size: { type: Number, default: 20 } },
  setup(/** @type {{name: string, size: number}} */ props) {
    return () => {
      const pascal = props.name.replace(/(^|-)(\w)/g, (_m, _s, c) => c.toUpperCase());
      /** @type {[string, Record<string, string>][]} */
      const nodes = lucide_.icons[pascal] || [];
      return h('svg', {
        xmlns: 'http://www.w3.org/2000/svg', width: props.size, height: props.size, viewBox: '0 0 24 24',
        fill: 'none', stroke: 'currentColor', 'stroke-width': 2,
        'stroke-linecap': 'round', 'stroke-linejoin': 'round',
      }, nodes.map(([tag, attrs]) => h(tag, attrs)));
    };
  },
};

/** list of strings; keeps one trailing blank row */
const StrList = {
  props: { modelValue: { type: Array, required: true } },
  methods: {
    /** @param {number} i @param {string} v */
    set(i, v) {
      const list = /** @type {string[]} */ (this.modelValue);
      list[i] = v;
      if (list[list.length - 1] !== '') list.push('');
    },
  },
  template: `
    <div class="flex flex-col gap-1">
      <input v-for="(v, i) in modelValue" :key="i" class="input input-sm w-full"
             :value="v" @input="set(i, $event.target.value)">
    </div>`,
};

/** list of names; keeps one trailing blank row */
const NameList = {
  props: {
    modelValue: { type: Array, required: true },
    parts: { type: Array, required: true },
  },
  methods: {
    grow() {
      const list = /** @type {Name[]} */ (this.modelValue);
      const last = list[list.length - 1];
      if (last && (last.family || last.given)) list.push(blankName(/** @type {string[]} */ (this.parts)));
    },
  },
  template: `
    <div class="flex flex-col gap-1">
      <div v-for="(n, i) in modelValue" :key="i" class="grid grid-cols-4 gap-1">
        <input v-for="p in parts" :key="p" class="input input-sm w-full" :placeholder="p"
               v-model="n[p]" @input="grow">
      </div>
    </div>`,
};

/** @param {string[]} parts */
const blankName = (parts) => Object.fromEntries(parts.map((p) => [p, '']));

/**
 * @param {FieldDef} def
 * @param {string[]} parts
 */
function blankValue(def, parts) {
  if (def.type === 'name') return [blankName(parts)];
  if (def.type === 'list') return [''];
  return '';
}

/**
 * @param {Source} source
 * @param {Schema} schema
 * @returns {Source}
 */
function toForm(source, schema) {
  const form = JSON.parse(JSON.stringify(source));
  form.aliases = [...(form.aliases || []), ''];
  form.extra = form.extra || {};
  for (const [name, def] of Object.entries(schema.fields)) {
    if (form[name] === undefined) continue;
    if (def.type === 'name') form[name] = [...form[name].map((/** @type {Name} */ n) => ({ ...blankName(schema.nameParts), ...n })), blankName(schema.nameParts)];
    else if (def.type === 'list') form[name] = [...form[name], ''];
  }
  return form;
}

/** @param {any} v */
const hasValue = (v) =>
  Array.isArray(v) ? v.some((x) => (typeof x === 'string' ? x : x.family || x.given)) : v !== undefined && v !== '';

const SourceForm = {
  components: { StrList, NameList, Icon },
  props: {
    schema: { type: Object, required: true },
    /** existing key, or null when new */
    editKey: { type: String, default: null },
    sources: { type: Array, required: true },
  },
  emits: ['error', 'saved', 'deleted'],
  setup(/** @type {any} */ props, /** @type {any} */ { emit }) {
    const /** @type {Schema} */ schema = props.schema;
    const form = ref(/** @type {Source} */ ({ key: '', entrytype: 'misc', aliases: [''], extra: {} }));
    const shown = ref(/** @type {string[]} */ ([]));
    let currentKey = props.editKey;
    let pendingSave = Promise.resolve();

    watch(() => props.editKey, () => {
      const existing = props.editKey && props.sources.find((/** @type {Source} */ s) => s.key === props.editKey);
      form.value = existing
        ? toForm(existing, schema)
        : { key: '', entrytype: 'misc', aliases: [''], extra: {} };
      shown.value = Object.keys(schema.fields).filter((f) => hasValue(form.value[f]));
    }, { immediate: true });

    function ensureDefaults() {
      for (const f of schema.entryTypes[form.value.entrytype] || []) {
        if (form.value[f] === undefined) form.value[f] = blankValue(schema.fields[f], schema.nameParts);
      }
    }
    watch(() => form.value.entrytype, ensureDefaults, { immediate: true });

    const visible = computed(() =>
      Object.keys(schema.fields).filter((f) =>
        (schema.entryTypes[form.value.entrytype] || []).includes(f) || shown.value.includes(f) || hasValue(form.value[f])));
    const hidden = computed(() => Object.keys(schema.fields).filter((f) => !visible.value.includes(f)));

    /** @param {string} f */
    function addField(f) {
      if (!f) return;
      if (form.value[f] === undefined) form.value[f] = blankValue(schema.fields[f], schema.nameParts);
      shown.value.push(f);
    }

    /** @param {string} f */
    function inputType(f) {
      const t = schema.fields[f].type;
      return t === 'integer' ? 'number' : t === 'uri' ? 'url' : 'text';
    }

    /** @param {string} s */
    const slugify = (s) => s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
      .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

    async function save() {
      if (!currentKey && !form.value.key.trim() && form.value.title?.trim()) {
        form.value.key = slugify(form.value.title);
      }
      if (!form.value.key.trim()) return;
      try {
        const saved = currentKey
          ? await api('PUT', `/api/sources/${encodeURIComponent(currentKey)}`, form.value)
          : await api('POST', '/api/sources', form.value);
        currentKey = saved.key;
        emit('saved', saved.key);
      } catch (e) { emit('error', e); }
    }

    function autosave() {
      pendingSave = pendingSave.then(save);
    }

    async function remove() {
      await pendingSave;
      if (!currentKey) return;
      try {
        const deleted = JSON.parse(JSON.stringify(form.value));
        await api('DELETE', `/api/sources/${encodeURIComponent(currentKey)}`);
        emit('deleted', deleted);
      } catch (e) { emit('error', e); }
    }

    return { form, visible, hidden, addField, inputType, autosave, remove, types: Object.keys(schema.entryTypes) };
  },
  template: `
    <div @focusout="autosave">
      <div class="flex gap-1 mb-4">
        <a href="#/" class="btn btn-square" title="back"><icon name="arrow-left"></icon></a>
        <button v-if="editKey" class="btn btn-square btn-error btn-outline" title="delete" @click="remove"><icon name="trash-2"></icon></button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2">
        <fieldset class="fieldset"><legend class="fieldset-legend">key</legend>
          <input class="input w-full" v-model="form.key" required></fieldset>
        <fieldset class="fieldset"><legend class="fieldset-legend">entrytype</legend>
          <select class="select w-full" v-model="form.entrytype"><option v-for="t in types" :key="t">{{ t }}</option></select></fieldset>
        <fieldset class="fieldset md:col-span-2"><legend class="fieldset-legend">title</legend>
          <input class="input w-full" v-model="form.title"></fieldset>
        <fieldset class="fieldset md:col-span-2"><legend class="fieldset-legend">aliases</legend>
          <str-list v-model="form.aliases"></str-list></fieldset>

        <fieldset v-for="f in visible" :key="f" class="fieldset"
                  :class="{'md:col-span-2': ['name', 'list', 'text'].includes(schema.fields[f].type)}">
          <legend class="fieldset-legend">{{ f }}</legend>
          <name-list v-if="schema.fields[f].type === 'name'" v-model="form[f]" :parts="schema.nameParts"></name-list>
          <str-list v-else-if="schema.fields[f].type === 'list'" v-model="form[f]"></str-list>
          <textarea v-else-if="schema.fields[f].type === 'text'" class="textarea w-full" v-model="form[f]"></textarea>
          <select v-else-if="schema.fields[f].choices" class="select w-full" v-model="form[f]">
            <option value=""></option><option v-for="c in schema.fields[f].choices" :key="c">{{ c }}</option>
          </select>
          <input v-else-if="schema.fields[f].type === 'integer'" class="input w-full" type="number" v-model.number="form[f]">
          <input v-else-if="schema.fields[f].type === 'date'" class="input w-full" placeholder="YYYY-MM-DD"
                 pattern="-?\\d{4}(-\\d{2}(-\\d{2})?)?(/(-?\\d{4}(-\\d{2}(-\\d{2})?)?)?)?" v-model="form[f]">
          <input v-else class="input w-full" :type="inputType(f)" v-model="form[f]">
        </fieldset>

        <fieldset v-for="(v, k) in form.extra" :key="'x' + k" class="fieldset">
          <legend class="fieldset-legend">{{ k }}</legend>
          <input class="input w-full" v-model="form.extra[k]">
        </fieldset>
      </div>
      <select class="select select-sm mt-4" @change="addField($event.target.value); $event.target.value = ''">
        <option value="">+ field</option>
        <option v-for="f in hidden" :key="f">{{ f }}</option>
      </select>
    </div>`,
};

/** @param {Source} s */
const authors = (s) => {
  const names = /** @type {Name[]} */ (s.author || s.editor || []);
  if (!names.length) return '';
  return names[0].family + (names.length > 1 ? ' et al.' : '');
};

const SourceList = {
  components: { Icon },
  props: { sources: { type: Array, required: true }, recent: { type: Array, required: true } },
  emits: ['error', 'imported', 'deleted', 'warn'],
  setup(/** @type {any} */ props, /** @type {any} */ { emit }) {
    const query = ref('');
    const rows = computed(() => {
      const q = query.value.trim().toLowerCase();
      return props.sources.filter((/** @type {Source} */ s) => {
        if (!q) return true;
        const hay = [s.key, s.title, ...(s.aliases || []), ...[...(s.author || []), ...(s.editor || [])].map((/** @type {Name} */ n) => `${n.given || ''} ${n.family || ''}`), s.date];
        return hay.some((x) => x && String(x).toLowerCase().includes(q));
      });
    });

    async function fromClipboard() {
      try {
        const text = await navigator.clipboard.readText();
        const created = await api('POST', '/api/import-bibtex', { text });
        emit('imported', created.map((/** @type {Source} */ s) => s.key));
      } catch (e) { emit('error', e); }
    }

    /** @param {string} text */
    async function copy(text) {
      try { await navigator.clipboard.writeText(text); } catch { emit('warn', 'Could not copy to clipboard'); }
    }

    /** @param {string} v */
    const escHtml = (v) => v.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    /** @param {Source} s */
    const copyMarkdown = (s) => copy(`[${(s.title || s.key).replace(/[[\]]/g, '\\$&')}](${s.url || ''})`);
    /** @param {Source} s */
    const copyHtml = (s) => copy(`<a href="${escHtml(s.url || '')}" target="_blank">${escHtml(s.title || s.key)}</a>`);

    /** @param {Source} s */
    async function remove(s) {
      try {
        await api('DELETE', `/api/sources/${encodeURIComponent(s.key)}`);
        emit('deleted', s);
      } catch (e) { emit('error', e); }
    }

    const recentBg = ['bg-yellow-400/50!', 'bg-yellow-400/30!', 'bg-yellow-400/15!'];
    /** @param {Source} s */
    const rowClass = (s) => recentBg[props.recent.indexOf(s.key)] || 'hover:bg-base-200';

    return { query, rows, rowClass, fromClipboard, authors, copy, copyMarkdown, copyHtml, remove, edit: (/** @type {string} */ key) => go('#/edit/' + encodeURIComponent(key)), year: (/** @type {Source} */ s) => (s.date || '').slice(0, 4) };
  },
  template: `
    <div>
      <div class="flex gap-1 mb-2">
        <a href="#/new" class="btn" title="new source"><icon name="plus"></icon>New</a>
        <button class="btn" title="add from bibtex (clipboard)" @click="fromClipboard"><icon name="clipboard-paste"></icon>Import BibTeX</button>
        <a href="#/settings" class="btn" title="settings"><icon name="settings"></icon>Settings</a>
      </div>
      <div class="mb-4">
        <input class="input w-full" type="search" v-model="query" placeholder="Filter" autofocus>
      </div>
      <table class="table table-xs table-zebra">
        <thead><tr><th></th><th>key</th><th>title</th><th>author</th><th>year</th><th>type</th><th></th></tr></thead>
        <tbody>
          <tr v-for="s in rows" :key="s.key" :class="rowClass(s)">
            <td><button class="btn btn-ghost btn-xs btn-square" title="copy key" @click="copy(s.key)"><icon name="copy" :size="14"></icon></button></td>
            <td class="font-mono">{{ s.key }}</td>
            <td>
              <div class="flex items-center justify-between gap-2">
                <span>{{ s.title }}</span>
                <span class="flex shrink-0">
                  <button class="btn btn-ghost btn-xs btn-square" title="copy as markdown link" @click="copyMarkdown(s)"><icon name="link" :size="14"></icon></button>
                  <button class="btn btn-ghost btn-xs btn-square" title="copy as html link" @click="copyHtml(s)"><icon name="code-xml" :size="14"></icon></button>
                </span>
              </div>
            </td>
            <td>{{ authors(s) }}</td><td>{{ year(s) }}</td><td>{{ s.entrytype }}</td>
            <td class="whitespace-nowrap text-right">
              <button class="btn btn-ghost btn-xs btn-square" title="edit" @click="edit(s.key)"><icon name="pencil" :size="14"></icon></button>
              <button class="btn btn-ghost btn-xs btn-square text-error" title="delete" @click="remove(s)"><icon name="trash-2" :size="14"></icon></button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>`,
};

const Settings = {
  components: { Icon },
  props: { path: { type: String, default: '' } },
  emits: ['error', 'saved'],
  setup(/** @type {any} */ props, /** @type {any} */ { emit }) {
    const value = ref(props.path || '');
    /** @typedef {{path: string, error: string | null, synced?: boolean}} BibRow */
    const bib = ref(/** @type {BibRow[]} */ ([{ path: '', error: null }]));
    let saved = '[]';

    /** @param {{bibtex: BibRow[]}} s */
    function setBib(s) {
      saved = JSON.stringify(s.bibtex.map((b) => b.path));
      bib.value = [...s.bibtex.map((b) => ({ ...b, synced: true })), { path: '', error: null }];
    }
    onMounted(async () => {
      try { setBib(await api('GET', '/api/settings')); } catch (e) { emit('error', e); }
    });

    async function save() {
      if (value.value === props.path) return;
      try {
        await api('PUT', '/api/settings', { path: value.value });
        emit('saved');
      } catch (e) { emit('error', e); }
    }

    /** @param {number} i @param {string} v */
    function setBibPath(i, v) {
      bib.value[i] = { path: v, error: null };
      if (bib.value[bib.value.length - 1].path !== '') bib.value.push({ path: '', error: null });
    }

    async function saveBib() {
      const paths = bib.value.map((b) => b.path.trim()).filter(Boolean);
      if (JSON.stringify(paths) === saved) return;
      try {
        setBib(await api('PUT', '/api/settings', { bibtex: paths }));
      } catch (e) { emit('error', e); }
    }

    return { value, save, bib, setBibPath, saveBib };
  },
  template: `
    <div>
      <div class="flex gap-1 mb-4">
        <a v-if="path" href="#/" class="btn btn-square" title="back"><icon name="arrow-left"></icon></a>
      </div>
      <fieldset class="fieldset"><legend class="fieldset-legend">data directory</legend>
        <input class="input w-full" v-model="value" @blur="save" autofocus></fieldset>
      <fieldset v-if="path" class="fieldset"><legend class="fieldset-legend">bibtex export</legend>
        <div class="flex flex-col gap-1" @focusout="saveBib">
          <div v-for="(b, i) in bib" :key="i">
            <label class="input input-sm w-full" :class="{'input-error': b.error}">
              <input class="grow font-mono" :value="b.path" placeholder="~/path/to/sources.bib"
                     @input="setBibPath(i, $event.target.value)" @keydown.enter="saveBib">
              <icon v-if="b.synced && !b.error" name="check" :size="14" class="text-success"></icon>
            </label>
            <div v-if="b.error" class="text-error text-xs mt-0.5">{{ b.error }}</div>
          </div>
        </div>
      </fieldset>
    </div>`,
};

createApp({
  components: { SourceForm, SourceList, Settings },
  setup() {
    const route = ref(location.hash || '#/');
    const error = ref('');
    const path = ref(/** @type {string | null} */ (null));
    const schema = ref(/** @type {Schema | null} */ (null));
    const sources = ref(/** @type {Source[]} */ ([]));
    const recent = ref(/** @type {string[]} */ ([]));
    const ready = ref(false);
    const deleted = ref(/** @type {Source | null} */ (null));
    const warning = ref('');
    let undoTimer = 0;
    let warnTimer = 0;

    /** @param {string} msg */
    function warn(msg) {
      warning.value = msg;
      clearTimeout(warnTimer);
      warnTimer = setTimeout(() => { warning.value = ''; }, 5000);
    }

    /** @param {any} e */
    const fail = (e) => { error.value = e.message || String(e); };

    async function loadSources() {
      try {
        [sources.value, recent.value] = await Promise.all([api('GET', '/api/sources'), api('GET', '/api/recent')]);
      } catch (e) { fail(e); }
    }

    async function init() {
      schema.value = await api('GET', '/api/schema');
      path.value = (await api('GET', '/api/settings')).path;
      if (!path.value) go('#/settings'); else await loadSources();
      ready.value = true;
    }

    addEventListener('hashchange', () => {
      route.value = location.hash || '#/';
      error.value = '';
      if (route.value === '#/' && path.value) loadSources();
    });

    const page = computed(() => {
      const r = route.value;
      if (r.startsWith('#/settings')) return 'settings';
      if (r === '#/new') return 'new';
      if (r.startsWith('#/edit/')) return 'edit';
      return 'list';
    });
    const editKey = computed(() => decodeURIComponent(route.value.slice('#/edit/'.length)));

    async function settingsSaved() {
      const first = !path.value;
      path.value = (await api('GET', '/api/settings')).path;
      await loadSources();
      if (first) go('#/');
    }

    /** @param {string | null} key */
    async function formSaved(key) {
      await loadSources();
      if (key && page.value === 'edit' && editKey.value !== key) {
        go(`#/edit/${encodeURIComponent(key)}`);
      }
    }

    /** @param {Source} source */
    async function formDeleted(source) {
      await loadSources();
      go('#/');
      deleted.value = source;
      clearTimeout(undoTimer);
      undoTimer = setTimeout(() => { deleted.value = null; }, 20000);
    }

    async function undoDelete() {
      if (!deleted.value) return;
      const source = deleted.value;
      try {
        await api('POST', '/api/sources', source);
        deleted.value = null;
        clearTimeout(undoTimer);
        await loadSources();
      } catch (e) { fail(e); }
    }

    /** @param {string[]} keys */
    async function imported(keys) {
      await loadSources();
      go(keys.length === 1 ? `#/edit/${encodeURIComponent(keys[0])}` : '#/');
    }

    onMounted(() => init().catch(fail));

    return { ready, error, path, schema, sources, recent, page, editKey, deleted, warning, warn, fail, settingsSaved, formSaved, formDeleted, undoDelete, imported };
  },
  template: `
    <div v-if="deleted || warning" class="toast toast-top toast-end z-50">
      <div v-if="warning" class="alert alert-warning shadow-lg"><span>{{ warning }}</span></div>
      <div v-if="deleted" class="alert shadow-lg">
        <span>{{ deleted.key }} deleted</span>
        <button class="btn btn-sm" @click="undoDelete">Undo</button>
      </div>
    </div>
    <div v-if="error" role="alert" class="alert alert-error mb-4"><span>{{ error }}</span></div>
    <template v-if="ready">
      <settings v-if="page === 'settings'" :path="path || ''" @saved="settingsSaved" @error="fail"></settings>
      <source-form v-else-if="page === 'new' || page === 'edit'" :key="page + editKey" :schema="schema"
                   :sources="sources" :edit-key="page === 'edit' ? editKey : null" @saved="formSaved" @deleted="formDeleted" @error="fail"></source-form>
      <source-list v-else :sources="sources" :recent="recent" @imported="imported" @deleted="formDeleted" @warn="warn" @error="fail"></source-list>
    </template>`,
}).mount('#app');
