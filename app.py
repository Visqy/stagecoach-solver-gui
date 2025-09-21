import json
import io
from typing import Any, Dict, List, Tuple, Optional
import streamlit as st

# Import stagecoach solver utilities from local module
try:
    from stagecoach import solve_stagecoach_dp, reconstruct_all_paths, draw_stagecoach_graph
except Exception as e:
    st.error(f'Gagal mengimpor modul stagecoach.py: {e}')
    st.stop()

# ------------------------------
# Konfigurasi Halaman & Tailwind
# ------------------------------
st.set_page_config(page_title='Stagecoach DP GUI', layout='wide', page_icon='🧭')

# Inject Tailwind via CDN
TAILWIND_CDN = '''
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<style>
  .chip { @apply inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 border border-gray-200; }
  .badge { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-100 text-indigo-700; }
  .card  { @apply bg-white shadow rounded-2xl p-5 border border-gray-100; }
  .muted { color: #6b7280; }
  .mono  { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
  .btn   { @apply inline-flex items-center justify-center px-4 py-2 rounded-lg font-medium border border-gray-200 shadow-sm bg-white hover:bg-gray-50; }
  .btn-primary { @apply inline-flex items-center justify-center px-4 py-2 rounded-lg font-semibold text-white bg-indigo-600 hover:bg-indigo-700; }
  .step   { @apply px-3 py-1 rounded-full text-sm; }
  .step-on { @apply bg-indigo-600 text-white; }
  .step-off{ @apply bg-gray-200 text-gray-700; }
</style>
'''
st.markdown(TAILWIND_CDN, unsafe_allow_html=True)

# HEADER = '''
# <div class="max-w-5xl mx-auto mt-2 mb-6">
#   <div class="flex items-center gap-3">
#     <h1 class="text-3xl font-bold">Stagecoach Dynamic Programming</h1>
#   </div>
# </div>
# '''
# st.markdown(HEADER, unsafe_allow_html=True)

# ------------------------------
# NAVBAR (judul di navbar + tombol Input/Output)
# ------------------------------
def render_navbar(active: int):
    with st.container():
        st.markdown('<div class="top-nav">', unsafe_allow_html=True)
        col1, col_sp, col2, col3 = st.columns([4, 4, 1, 1])
        with col1:
            st.markdown(
                '''
                <div class="max-w-5xl mx-auto py-3">
                  <div class="flex items-center gap-3">
                    <div class="text-xl font-bold">Stagecoach Dynamic Programming</div>
                    <span class="badge">Stagecoach DP</span>
                  </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
        with col2:
            if st.button('Input', type='primary' if active == 1 else 'secondary'):
                go('input'); st.rerun()
        with col3:
            if st.button('Output', type='primary' if active == 2 else 'secondary'):
                go('output'); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------
# Defaults
# ------------------------------
DEFAULT_LAYERS = [['S'], ['A', 'B'], ['C', 'D'], ['T']]
DEFAULT_EDGES = {
    'S': {'A': 2, 'B': 5},
    'A': {'C': 4, 'D': 1},
    'B': {'C': 2},
    'C': {'T': 3},
    'D': {'T': 2}
}
DEFAULT_START = 'S'
DEFAULT_GOAL = 'T'
DEFAULT_OPT_MODE = 'min'
DEFAULT_COMBINE_OP = '+'

# ------------------------------
# Helpers
# ------------------------------
def _safe_json_loads(s: str) -> Any:
    try:
        return json.loads(s)
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def parse_inputs(layers_str: str, edges_str: str, start: str, goal: str,
                 opt_mode: str, combine_op: str,
                 uploaded_content: Optional[bytes]) -> Tuple[List[List[str]], Dict[str, Dict[str, float]], str, str, str, str]:
    cfg = {}
    if uploaded_content:
        cfg = json.loads(uploaded_content.decode('utf-8'))

    layers = cfg.get('layers')
    if layers is None:
        layers = _safe_json_loads(layers_str)

    edges = cfg.get('edges')
    if edges is None:
        edges = _safe_json_loads(edges_str)

    start_i = cfg.get('start', start)
    goal_i = cfg.get('goal', goal)
    opt_i = cfg.get('opt_mode', opt_mode)
    op_i = cfg.get('combine_op', combine_op)
    return layers, edges, start_i, goal_i, opt_i, op_i

def build_stage_index(layers: List[List[str]]) -> Dict[str, int]:
    idx = {}
    for i, stage_nodes in enumerate(layers):
        for node in stage_nodes:
            idx[node] = i
    return idx

def validate_layers_edges(layers: Any, edges: Any, start: str, goal: str) -> List[str]:
    errors = []
    if not isinstance(layers, list) or not all(isinstance(s, list) for s in layers):
        errors.append('`layers` harus berupa list of list, misal: [["S"],["A","B"],["T"]].')
        return errors

    seen = set()
    for s in layers:
        for n in s:
            if not isinstance(n, str):
                errors.append('Setiap node di layers harus string.')
                break
            if n in seen:
                errors.append(f'Node duplikat terdeteksi: {n}')
            seen.add(n)

    if not isinstance(edges, dict):
        errors.append('`edges` harus berupa dict-of-dict, misal: {"S":{"A":2}}.')
        return errors

    stage_of = build_stage_index(layers)
    if start not in stage_of:
        errors.append(f"Start node '{start}' tidak ada di layers.")
    if goal not in stage_of:
        errors.append(f"Goal node '{goal}' tidak ada di layers.")
    if errors:
        return errors

    for u, nbrs in edges.items():
        if u not in stage_of:
            errors.append(f"Node sumber '{u}' pada edges tidak ada di layers.")
            continue
        if not isinstance(nbrs, dict):
            errors.append(f"Edges dari '{u}' harus dict, misal: \"{u}\":{{\"V\":cost}}.")
            continue
        su = stage_of[u]
        for v, w in nbrs.items():
            if v not in stage_of:
                errors.append(f"Node target '{v}' pada edges tidak ada di layers.")
                continue
            sv = stage_of[v]
            if sv != su + 1:
                errors.append(f"Edge {u}->{v} melompat stage (dari {su} ke {sv}). Harus i -> i+1.")
            try:
                float(w)
            except Exception:
                errors.append(f'Bobot edge {u}->{v} bukan angka: {w}')
    return errors

def chips_path(path: List[str]) -> str:
    if not path:
        return '<span class="muted">-</span>'
    parts = []
    for i, n in enumerate(path):
        parts.append(f'<span class="chip">{n}</span>')
        if i < len(path) - 1:
            parts.append('<span class="mx-1">&rarr;</span>')
    return ''.join(parts)

# ------------------------------
# Session State
# ------------------------------
if 'page' not in st.session_state:
    st.session_state.page = 'input'   # 'input' | 'output'
if 'cfg' not in st.session_state:
    st.session_state.cfg = None
if 'result' not in st.session_state:
    st.session_state.result = None
if 'all_paths' not in st.session_state:
    st.session_state.all_paths = []
if 'presets' not in st.session_state:
    st.session_state.presets = {}  # name -> cfg dict

def go(page: str):
    st.session_state.page = page

# ------------------------------
# PAGE: INPUT
# ------------------------------
if st.session_state.page == 'input':
    render_navbar(1)
    with st.form('input_form', clear_on_submit=False):
        st.markdown('<div class="max-w-5xl mx-auto">', unsafe_allow_html=True)

        st.markdown('<div class="card mb-4">', unsafe_allow_html=True)
        st.subheader('Konfigurasi')
        st.caption('Masukkan atau unggah berkas konfigurasi.')
        colA, colB = st.columns([1,1])
        with colA:
            layers_str = st.text_area('Layers', value=json.dumps(DEFAULT_LAYERS), height=160)
            start = st.text_input('Start', value=DEFAULT_START)
            opt_mode = st.selectbox('Mode Optimasi', ['min', 'max'], index=0)
        with colB:
            edges_str  = st.text_area('Edges',  value=json.dumps(DEFAULT_EDGES), height=160)
            goal  = st.text_input('Goal',  value=DEFAULT_GOAL)
            combine_op = st.selectbox('Operasi Agregasi', ['+', '*'], index=0)

        uploaded = st.file_uploader('Upload JSON (opsional)', type=['json'])

        st.markdown('</div>', unsafe_allow_html=True)

        col_btn1, col_btn2, col_btn3 = st.columns([1,1,8])
        with col_btn1:
            use_example = st.form_submit_button('Gunakan Contoh')
        with col_btn2:
            submitted = st.form_submit_button('Jalankan Solver', type='primary')

        st.markdown('</div>', unsafe_allow_html=True)

    # Handle form actions
    if use_example:
        layers_str = json.dumps(DEFAULT_LAYERS)
        edges_str  = json.dumps(DEFAULT_EDGES)
        start = DEFAULT_START
        goal  = DEFAULT_GOAL
        opt_mode = DEFAULT_OPT_MODE
        combine_op = DEFAULT_COMBINE_OP
        st.rerun()

    if submitted:
        try:
            layers, edges, start_i, goal_i, opt_i, op_i = parse_inputs(
                layers_str, edges_str, start, goal, opt_mode, combine_op, uploaded.read() if uploaded else None
            )
        except Exception as e:
            st.error(f'Gagal membaca input: {e}')
            st.stop()

        errors = validate_layers_edges(layers, edges, start_i, goal_i)
        if errors:
            st.error('Input tidak valid. Perbaiki hal berikut:')
            for err in errors:
                st.markdown(f'- {err}')
            with st.expander('Lihat contoh input yang valid'):
                st.code(json.dumps({
                    'layers': DEFAULT_LAYERS,
                    'edges': DEFAULT_EDGES,
                    'start': DEFAULT_START,
                    'goal': DEFAULT_GOAL,
                    'opt_mode': DEFAULT_OPT_MODE,
                    'combine_op': DEFAULT_COMBINE_OP
                }, indent=2), language='json')
        else:
            with st.spinner('Menghitung...'):
                try:
                    result = solve_stagecoach_dp(
                        layers, edges, start_i, goal_i,
                        opt_mode=opt_i, combine_op=op_i, print_tables=False
                    )
                except TypeError:
                    result = solve_stagecoach_dp(
                        layers, edges, start_i, goal_i,
                        opt_mode=opt_i, combine_op=op_i
                    )
                try:
                    all_paths = reconstruct_all_paths(result.policy, start_i, goal_i)
                except Exception:
                    all_paths = [getattr(result, 'path', [])]

            st.session_state.cfg = dict(layers=layers, edges=edges, start=start_i, goal=goal_i,
                                        opt_mode=opt_i, combine_op=op_i)
            st.session_state.result = result
            st.session_state.all_paths = all_paths
            go('output')
            st.rerun()

# ------------------------------
# PAGE: OUTPUT
# ------------------------------
if st.session_state.page == 'output':
    render_navbar(2)
    cfg = st.session_state.cfg
    result = st.session_state.result
    all_paths = st.session_state.all_paths or []

    # Tombol kembali
    st.markdown('<div class="max-w-5xl mx-auto mb-3">', unsafe_allow_html=True)
    col_back, col_sp = st.columns([1,6])
    with col_back:
        if st.button('← Kembali ke Input', key='back_to_input', help='Edit konfigurasi dan jalankan ulang'):
            go('input')
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if not cfg or not result:
        st.info('Belum ada hasil. Silakan kembali ke halaman Input.')
    else:
        tab1, tab2, tab3, tab4 = st.tabs(['Hasil', 'Proses', 'Visualisasi', 'Tentang'])

        with tab1:
            st.markdown('<div class="max-w-5xl mx-auto grid md:grid-cols-3 gap-4">', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="muted text-xs mb-1">Optimal Cost</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="text-2xl font-semibold">{getattr(result, "optimal_cost", "-")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="muted text-xs mb-1">Path Terpilih</div>', unsafe_allow_html=True)
            st.markdown(chips_path(getattr(result, 'path', [])), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="muted text-xs mb-1">Opsi</div>', unsafe_allow_html=True)
            st.markdown(
                f'<span class="badge mr-2">Tujuan: {cfg["opt_mode"]}</span>'
                f'<span class="badge">Operator: {cfg["combine_op"]}</span>',
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('### Semua Jalur Optimal')
            st.dataframe({'Jalur': [' → '.join(p) for p in all_paths]})

        with tab2:
            st.markdown('### Tabel Proses per Stage')
            if hasattr(result, 'tables') and isinstance(result.tables, list) and result.tables:
                for i, t in enumerate(result.tables[::-1]):
                    with st.expander(f'Stage {len(result.tables)-i} (mundur)'):
                        st.code(t, language='text')
            else:
                st.info('Solver tidak mengembalikan `result.tables`.')

        with tab3:
            st.markdown('### Visualisasi Jalur')
            show_all = st.toggle('Tampilkan semua jalur optimal', value=True)
            draw_paths = all_paths if show_all and all_paths else [getattr(result, 'path', [])]

            buf = io.BytesIO()
            try:
                draw_stagecoach_graph(cfg['layers'], cfg['edges'],
                                      start=cfg['start'], goal=cfg['goal'],
                                      opt_mode=cfg['opt_mode'], paths=draw_paths, save_path=buf)
            except TypeError:
                draw_stagecoach_graph(cfg['layers'], cfg['edges'],
                                      cfg['start'], cfg['goal'], cfg['opt_mode'], draw_paths, buf)
            buf.seek(0)
            st.image(buf, caption='Grafik Stagecoach')
            st.download_button('Unduh PNG', data=buf.getvalue(), file_name='stagecoach.png', mime='image/png')

        with tab4:
            st.markdown('#### Ringkas')
            st.write(
                '- **Stagecoach DP** menyelesaikan rute optimal di graf ber-stage.\\n'
                '- `opt_mode=min|max` menentukan minimisasi/maksimisasi biaya.\\n'
                '- `combine_op=+|*` menentukan operasi agregasi biaya antaredge.\\n'
                '- Pastikan edges hanya menghubungkan stage i ke i+1.'
            )
            st.markdown('#### Konfigurasi Terakhir')
            st.code(json.dumps(cfg, indent=2), language='json')
            # ====== SIMPAN / MUAT KONFIGURASI ======
            st.markdown('<div class="max-w-5xl mx-auto">', unsafe_allow_html=True)
            with st.expander('Simpan / Muat Konfigurasi', expanded=True):
                preset_name = st.text_input('Nama preset', value='konfigurasi-1')
                json_bytes = json.dumps(cfg, indent=2).encode('utf-8')
                file_name = f"{(preset_name or 'stagecoach-config').strip()}.json"

                cA, cB, cC = st.columns([1,1,2])
                with cA:
                    st.download_button('Unduh JSON Konfigurasi', data=json_bytes, file_name=file_name, mime='application/json')
                with cB:
                    if st.button('Simpan sebagai Preset (session)'):
                        name = (preset_name or f'preset-{len(st.session_state.presets)+1}').strip()
                        st.session_state.presets[name] = dict(cfg)  # shallow copy is fine
                        st.success(f'Preset \"{name}\" disimpan di session.')

                if st.session_state.presets:
                    st.markdown('**Preset Tersimpan (session):**')
                    for name, pcfg in st.session_state.presets.items():
                        col1, col2 = st.columns([5,1])
                        with col1:
                            st.code(json.dumps(pcfg, indent=2), language='json')
                        with col2:
                            if st.button(f'Muat: {name}', key=f'load_{name}'):
                                st.session_state.cfg = pcfg
                                go('input')
                                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)