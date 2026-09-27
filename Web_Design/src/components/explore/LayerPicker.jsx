import { useEffect, useId, useRef, useState } from 'react';
import { MENU, RURAL_PREFIX, menuItem, menuLabel } from '../../data/layerMenu';
import { GAP_COLORS } from '../../data/mapResearch';
import { STATE_COLORS, rampFor } from '../../data/conversionScale';

function badge(id, layer) {
  if (id.startsWith(RURAL_PREFIX)) return '1990–2024';
  if (!layer) return '';
  if (layer.temporal === 'timeline') return `${layer.years[0]}–${layer.years[1]}`;
  if (layer.temporal === 'waves') return `Survey waves ${layer.years[0]}–${layer.years.at(-1)}`;
  return 'Latest';
}

function ramp(id, layer) {
  if (id.startsWith(RURAL_PREFIX)) return GAP_COLORS;
  if (!layer) return ['#2c2c31'];
  return layer.scale.kind === 'categorical' ? Object.values(STATE_COLORS) : rampFor(layer);
}

/**
 * "Analysis dimension" picker: a button that opens a card panel with two tabs (annual series vs
 * latest snapshots). Selecting a card closes the panel and returns focus to the button.
 */
export default function LayerPicker({ selected, layerById, onSelect, onOpen }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState(() => menuItem(selected)?.tab.id ?? 'time');
  const buttonRef = useRef(null);
  const panelRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event) => {
      if (event.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    const onPointer = (event) => {
      if (!panelRef.current?.contains(event.target) && !buttonRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    panelRef.current?.querySelector('[aria-selected="true"]')?.focus();
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [open]);

  const toggle = () => {
    if (!open) {
      setTab(menuItem(selected)?.tab.id ?? 'time');
      onOpen?.();
    }
    setOpen((value) => !value);
  };
  const choose = (itemId) => {
    onSelect(itemId);
    setOpen(false);
    buttonRef.current?.focus();
  };
  const onTabKey = (event) => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    const next = MENU[(MENU.findIndex((t) => t.id === tab) + 1) % MENU.length].id;
    setTab(next);
    document.getElementById(`${id}-tab-${next}`)?.focus();
  };
  const current = MENU.find((t) => t.id === tab);

  return (
    <div className='layer-picker'>
      <span className='layer-picker-label' id={`${id}-label`}>Analysis dimension</span>
      <button
        ref={buttonRef}
        type='button'
        className='layer-picker-button'
        aria-haspopup='dialog'
        aria-expanded={open}
        aria-controls={`${id}-panel`}
        aria-labelledby={`${id}-label ${id}-current`}
        onClick={toggle}
      >
        <span id={`${id}-current`}>{menuLabel(selected, selected)}</span>
        <span aria-hidden='true'>▾</span>
      </button>
      {open && (
        <div ref={panelRef} id={`${id}-panel`} className='layer-picker-panel' role='dialog' aria-label='Choose what the map shows'>
          <div className='layer-picker-tabs' role='tablist' aria-label='Type of map'>
            {MENU.map((t) => (
              <button
                key={t.id}
                id={`${id}-tab-${t.id}`}
                type='button'
                role='tab'
                aria-selected={tab === t.id}
                aria-controls={`${id}-tabpanel`}
                tabIndex={tab === t.id ? 0 : -1}
                onKeyDown={onTabKey}
                onClick={() => setTab(t.id)}
              >
                <strong>{t.label}</strong>
                <small>{t.hint}</small>
              </button>
            ))}
          </div>
          <div id={`${id}-tabpanel`} role='tabpanel' aria-labelledby={`${id}-tab-${tab}`} className='layer-picker-groups'>
            {current.groups.map((group) => (
              <section key={group.label} className='layer-picker-group'>
                <h3>{group.label}</h3>
                <p>{group.note}</p>
                <div className='layer-picker-cards'>
                  {group.items.map((item) => {
                    const layer = layerById?.[item.id];
                    const colors = ramp(item.id, layer);
                    return (
                      <button
                        key={item.id}
                        type='button'
                        className='layer-card'
                        aria-pressed={selected === item.id}
                        title={layer ? `${layer.question} ${layer.caveat}` : item.question}
                        onClick={() => choose(item.id)}
                      >
                        <span className='layer-card-ramp' aria-hidden='true'>
                          {colors.map((color, i) => <i key={i} style={{ background: color }} />)}
                        </span>
                        <strong>{item.label}</strong>
                        <span className='layer-card-question'>{item.question}</span>
                        <span className='layer-card-badge'>{badge(item.id, layer) || '…'}</span>
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
