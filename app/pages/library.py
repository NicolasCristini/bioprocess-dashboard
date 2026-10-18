import streamlit as st

from bioprocess.defaults import example_scenario
from bioprocess.io.scenario_file import from_text, to_yaml
from bioprocess.io.store import slug
from ui import state

store = state.store()
sc = state.sc()
st.title("My scenarios")
st.caption(state.STORAGE_NOTE)

c1, c2, c3 = st.columns([2, 1, 1])
existing = {d["name"] for d in store.list()}
status = "● unsaved changes" if state.unsaved() or sc.name not in existing else "saved"
c1.markdown(f"**Current:** {sc.name}  · {status}")
if c2.button("💾 Save", width="stretch", type="primary"):
    store.save(sc)
    state.replace(sc, saved=True)
    st.toast(f"Saved “{sc.name}”.")
    st.rerun()
with c3.popover("Save as copy…", width="stretch"):
    new_name = st.text_input("New name", f"{sc.name} (copy)")
    if st.button("Save copy", disabled=not new_name.strip()):
        copy = sc.model_copy(deep=True, update={"name": new_name.strip()})
        store.save(copy)
        state.replace(copy, saved=True)
        st.rerun()
if sc.name in existing and state.unsaved():
    st.caption(f"Saving overwrites the stored “{sc.name}”.")

st.divider()
items = store.list()
if not items:
    st.info("No saved scenarios yet.")
for d in items:
    a, b, c, e, f = st.columns([4, 2, 1, 1, 1])
    a.markdown(f"**{d['name']}**" + ("" if d["ok"] else "  ⚠ unreadable"))
    b.caption(d["modified"].strftime("%Y-%m-%d %H:%M"))
    if c.button("Open", key=f"open_{d['file']}", disabled=not d["ok"]):
        state.replace(store.load(d["file"]), saved=True)
        st.switch_page("pages/p4_results.py")
    e.download_button("⬇", (store.root / d["file"]).read_bytes(), d["file"], "application/x-yaml",
                      key=f"dl_{d['file']}", help="Download YAML")
    with f.popover("🗑"):
        st.write(f"Delete “{d['name']}”?")
        if st.button("Delete", key=f"del_{d['file']}", type="primary"):
            store.delete(d["file"])
            st.rerun()

st.divider()
u1, u2 = st.columns(2)
with u1:
    st.markdown("**Import**")
    up = st.file_uploader("Scenario (.yaml/.json) or backup (.zip)", type=["yaml", "yml", "json", "zip"])
    if up is not None and st.session_state.get("_lib_up") != up.file_id:
        st.session_state._lib_up = up.file_id
        try:
            if up.name.endswith(".zip"):
                st.success(f"Imported {store.import_zip(up.getvalue())} scenarios.")
            else:
                imported = from_text(up.getvalue().decode("utf-8"))
                store.save(imported)
                st.success(f"Imported “{imported.name}”.")
            st.rerun()
        except (ValueError, KeyError) as err:
            st.error(str(err))
with u2:
    st.markdown("**Backup / new**")
    st.download_button("⬇ Export all (.zip)", store.export_all(), "scenarios_backup.zip", "application/zip",
                       disabled=not items)
    st.download_button("⬇ Current as YAML", to_yaml(sc), f"{slug(sc.name)}.yaml", "application/x-yaml")
    if st.button("New from example"):
        state.replace(example_scenario(), example=True)
        st.switch_page("pages/p1_setup.py")

with st.expander("Clear my data"):
    st.write("Deletes every saved scenario from this " + ("browser." if "browser" in state.STORAGE_NOTE else "folder."))
    sure = st.checkbox("I have a backup or do not need them")
    if st.button("Delete all saved scenarios", disabled=not sure, type="primary"):
        st.success(f"Deleted {store.clear()} scenarios.")
        st.rerun()
