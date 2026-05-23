/* global React, ASPECT_GLYPHS, ASPECT_LABEL, OrnamentCorner, OrnamentDivider, OrnamentSpine, DropCap, FiligreeFrame, IconFireball, IconFrostbolt, IconArc, IconFlameWall, IconComet, IconHeraldAsh, ItemIcon, SocketFrame, ConstellationBackdrop */

// =========================================================================
// VELGRAD — Inventar (Equipment + Bag + Tooltip)
// Diegetic: opened occult tome — left page = paper-doll with equipped gear,
// right page = bag grid + item description.
// =========================================================================

const InventoryScreen = ({ aspect = "valsa" }) => {
  const A = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;
  return (
    <div className="vg-page" style={{
      position: "relative", width: 1760, height: 1100,
      padding: 48,
      display: "grid", gridTemplateColumns: "1fr 32px 1fr", gap: 0,
    }}>
      <ConstellationBackdrop density={50} opacity={0.25} seed={11}/>

      {/* HEADER — running head across both pages */}
      <InventoryHeader/>

      {/* LEFT PAGE — Paper doll */}
      <div style={{ position: "relative", paddingTop: 80, paddingInline: 24 }}>
        <PaperDollPage aspect={aspect}/>
      </div>

      {/* CENTER GUTTER — bronze spine */}
      <div style={{
        position: "relative", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "stretch", paddingTop: 80, paddingBottom: 40,
      }}>
        <div style={{ position: "absolute", inset: "80px 0 40px",
          background: "linear-gradient(180deg, transparent, rgba(0,0,0,0.55) 12%, rgba(0,0,0,0.55) 88%, transparent)",
          width: 28, left: "50%", transform: "translateX(-50%)" }}/>
        <OrnamentSpine height={920}/>
      </div>

      {/* RIGHT PAGE — Bag + tooltip */}
      <div style={{ position: "relative", paddingTop: 80, paddingInline: 24 }}>
        <BagPage/>
      </div>

      {/* FOOTER — running foot, folio number, catchword */}
      <InventoryFooter/>
    </div>
  );
};

// -------------------------------------------------------------------------
// HEADER & FOOTER (running head/foot like an occult manuscript)
// -------------------------------------------------------------------------

const InventoryHeader = () => (
  <div style={{
    position: "absolute", top: 32, left: 56, right: 56,
    display: "flex", alignItems: "center", justifyContent: "space-between",
  }}>
    <div style={{
      fontFamily: "var(--vg-display)", fontSize: 11, letterSpacing: "0.45em",
      color: "var(--vg-bronze-warm)", textTransform: "uppercase",
    }}>Codex&nbsp;Sartum &nbsp;·&nbsp; Liber&nbsp;Rerum</div>
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <div style={{
        fontFamily: "var(--vg-display)", fontSize: 22, letterSpacing: "0.28em",
        color: "var(--vg-aspect-halo)", textShadow: "0 0 18px var(--vg-aspect)", fontWeight: 700,
      }}>D&nbsp;I&nbsp;E&nbsp; &nbsp;A&nbsp;U&nbsp;S&nbsp;R&nbsp;Ü&nbsp;S&nbsp;T&nbsp;U&nbsp;N&nbsp;G</div>
      <div style={{ width: 220 }}><OrnamentDivider width={220} color="var(--vg-bronze)"/></div>
    </div>
    <div style={{
      fontFamily: "var(--vg-mono)", fontSize: 11, letterSpacing: "0.18em",
      color: "var(--vg-bronze-light)",
    }}>FOL.&nbsp;CXII&nbsp;·&nbsp;recto</div>
  </div>
);

const InventoryFooter = () => (
  <div style={{
    position: "absolute", bottom: 28, left: 56, right: 56,
    display: "flex", justifyContent: "space-between", alignItems: "center",
  }}>
    <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 12, color: "var(--vg-bronze-warm)", opacity: 0.85 }}>
      „Was du trägst, erinnert sich, dass es einmal jemandem gehörte."
    </div>
    <OrnamentDivider width={180} color="var(--vg-bronze-deep)"/>
    <div style={{ fontFamily: "var(--vg-mono)", fontSize: 10, letterSpacing: "0.2em", color: "var(--vg-bronze-warm)" }}>
      — der Sonnenfresser folgt —
    </div>
  </div>
);

// -------------------------------------------------------------------------
// LEFT — PAPER-DOLL PAGE
// -------------------------------------------------------------------------

const PaperDollPage = ({ aspect }) => {
  const A = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;
  const equipped = {
    helm:    { kind: "helm",   name: "Aschen-Kapuze",        rarity: "rare",   suffix: "Funkenwurf" },
    amulet:  { kind: "amulet", name: "Stunden-Anhänger",     rarity: "unique", suffix: "Nheyra-Pakt" },
    weapon:  { kind: "staff",  name: "Stab des Hohlen Wortes", rarity: "unique", suffix: "Im-Nesh-getragen" },
    offhand: { kind: "tome",   name: "Liber Ardens",         rarity: "rare",   suffix: "Asche-Echo" },
    chest:   { kind: "robe",   name: "Robe der Funkengeborenen", rarity: "rare",   suffix: "Brand-resistent" },
    gloves:  { kind: "gloves", name: "Asch-Stulpen",         rarity: "magic",  suffix: "Schnellen Zauber" },
    belt:    { kind: "belt",   name: "Gürtel der drei Tränke", rarity: "magic", suffix: "Drei-Fass" },
    boots:   { kind: "boots",  name: "Wandel-Schuhe",        rarity: "rare",   suffix: "Salz-treu" },
    ring1:   { kind: "ring",   name: "Ring der ersten Flamme", rarity: "unique", suffix: "Valsa-Echo" },
    ring2:   { kind: "ring",   name: "Aschring",             rarity: "rare",   suffix: "Anhalter" },
    flask1:  { kind: "flask",  name: "Tinktur d. Hohen Gewässer", rarity: "magic", suffix: "schnell" },
    flask2:  { kind: "flask",  name: "Geist-Elixier",        rarity: "magic", suffix: "anhaltend" },
  };

  // attribute snapshot
  const attrs = [
    { label: "Stärke",     val: 64,  color: "var(--vg-blood-bright)" },
    { label: "Geschick",   val: 82,  color: "var(--vg-aspect-bright)" },
    { label: "Intellekt",  val: 246, color: "var(--vg-ghost-bright)" },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 18, alignItems: "start" }}>
      {/* LEFT COLUMN — armour pieces */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <EquipSlot {...equipped.helm}    label="Haupt" />
        <EquipSlot {...equipped.amulet}  label="Hals"  size={64}/>
        <EquipSlot {...equipped.chest}   label="Leib"  size={92}/>
        <EquipSlot {...equipped.gloves}  label="Hände" />
        <EquipSlot {...equipped.ring1}   label="Ring I" size={56}/>
      </div>

      {/* CENTER — paper-doll */}
      <div style={{
        position: "relative", width: 320, height: 720,
        display: "flex", flexDirection: "column", alignItems: "center",
      }}>
        {/* aspect glyph behind doll */}
        <div style={{
          position: "absolute", inset: 0, display: "grid", placeItems: "center",
          color: "var(--vg-aspect-deep)", opacity: 0.32,
        }}>
          <A size={420}/>
        </div>

        {/* doll silhouette */}
        <svg viewBox="0 0 320 720" width="320" height="720" style={{ position: "relative", zIndex: 1 }}>
          <defs>
            <radialGradient id="aura" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="var(--vg-aspect-bright)" stopOpacity="0.35"/>
              <stop offset="100%" stopColor="var(--vg-aspect-bright)" stopOpacity="0"/>
            </radialGradient>
          </defs>
          {/* aura */}
          <ellipse cx="160" cy="360" rx="120" ry="280" fill="url(#aura)"/>
          {/* shadow on ground */}
          <ellipse cx="160" cy="680" rx="80" ry="14" fill="#000" opacity="0.55"/>
          {/* figure */}
          <g fill="#0a0604" stroke="#5a3f24" strokeWidth="1.2" strokeLinejoin="round">
            {/* head */}
            <ellipse cx="160" cy="120" rx="34" ry="40"/>
            {/* hood */}
            <path d="M122 110 C122 78 138 64 160 64 C182 64 198 78 198 110 L194 130 C188 110 170 102 160 102 C150 102 132 110 126 130 Z" fill="#06030a"/>
            {/* torso & robe */}
            <path d="M118 170 L150 174 L170 174 L202 170 L218 220 L208 360 L194 480 L190 580 L130 580 L126 480 L112 360 L102 220 Z"/>
            {/* belt line */}
            <path d="M118 360 L202 360" stroke="#3b2818" strokeWidth="2"/>
            {/* sleeves */}
            <path d="M104 226 L80 280 L72 360 L96 372" fill="#06030a"/>
            <path d="M216 226 L240 280 L248 360 L224 372" fill="#06030a"/>
            {/* hands */}
            <circle cx="78"  cy="372" r="10"/>
            <circle cx="242" cy="372" r="10"/>
            {/* boots */}
            <path d="M130 580 L132 660 L150 668 L150 580 Z M170 580 L170 668 L188 660 L190 580 Z" fill="#06030a"/>
            {/* face shadow */}
            <ellipse cx="160" cy="130" rx="22" ry="20" fill="#06030a"/>
            <line x1="148" y1="128" x2="156" y2="128" stroke="var(--vg-aspect-bright)" strokeWidth="2" opacity="0.85"/>
            <line x1="164" y1="128" x2="172" y2="128" stroke="var(--vg-aspect-bright)" strokeWidth="2" opacity="0.85"/>
          </g>
        </svg>

        {/* attribute readout below doll */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          display: "flex", justifyContent: "space-around", gap: 8, padding: "10px 12px",
          background: "linear-gradient(180deg, transparent, rgba(0,0,0,0.45))",
        }}>
          {attrs.map(a => (
            <div key={a.label} style={{ textAlign: "center" }}>
              <div style={{ fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.3em", color: "var(--vg-bronze-warm)" }}>{a.label.toUpperCase()}</div>
              <div style={{ fontFamily: "var(--vg-display)", fontSize: 24, fontWeight: 800, color: a.color, textShadow: "0 0 8px #000" }}>{a.val}</div>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT COLUMN */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <EquipSlot {...equipped.weapon}  label="Stab" size={92}/>
        <EquipSlot {...equipped.offhand} label="Fokus"/>
        <EquipSlot {...equipped.belt}    label="Gürtel"/>
        <EquipSlot {...equipped.boots}   label="Füße"/>
        <EquipSlot {...equipped.ring2}   label="Ring II" size={56}/>
      </div>

      {/* below grid — DEFENSES + RESISTANCES + FLASKS */}
      <div style={{ gridColumn: "1 / -1", marginTop: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        <DefenseCard/>
        <ResistCard/>
      </div>
    </div>
  );
};

const EquipSlot = ({ kind, name, rarity, suffix, label, size = 76 }) => {
  const rarityColor = {
    common:   "var(--vg-vellum-mid)",
    magic:    "var(--vg-ghost-bright)",
    rare:     "var(--vg-gold-bright)",
    unique:   "#c9742a",
    mythic:   "var(--vg-blood-glow)",
  }[rarity];
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <div style={{
        position: "relative",
        width: size, height: size,
        background: "linear-gradient(160deg, #0c0704 0%, #1c1208 50%, #050200 100%)",
        border: `1px solid ${rarityColor}`,
        boxShadow: `inset 0 0 14px rgba(0,0,0,0.85), 0 0 12px ${rarityColor}33, 0 0 0 1px rgba(0,0,0,0.5)`,
        color: rarityColor,
        display: "grid", placeItems: "center",
      }}>
        <span style={{ position:"absolute", top:-2, left:-2, width:5, height:5, background: rarityColor }}/>
        <span style={{ position:"absolute", top:-2, right:-2, width:5, height:5, background: rarityColor }}/>
        <span style={{ position:"absolute", bottom:-2, left:-2, width:5, height:5, background: rarityColor }}/>
        <span style={{ position:"absolute", bottom:-2, right:-2, width:5, height:5, background: rarityColor }}/>
        <ItemIcon kind={kind} size={size - 16} color={rarityColor}/>
        {/* sockets pip */}
        <div style={{ position: "absolute", bottom: 4, right: 4, display: "flex", gap: 2 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <span key={i} style={{ width: 5, height: 5, borderRadius: "50%", background: i < 2 ? "var(--vg-gold-bright)" : "transparent", border: "1px solid var(--vg-bronze-deep)" }}/>
          ))}
        </div>
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: "var(--vg-display)", fontSize: 8, letterSpacing: "0.25em", color: "var(--vg-bronze)", textTransform: "uppercase" }}>{label}</div>
        <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.08em", color: rarityColor, textTransform: "uppercase", marginTop: 2, lineHeight: 1.1 }}>{name}</div>
      </div>
    </div>
  );
};

const DefenseCard = () => (
  <div style={{
    border: "1px solid var(--vg-bronze-deep)", padding: 14,
    background: "rgba(8,5,3,0.5)",
  }}>
    <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)", marginBottom: 10 }}>VERTEIDIGUNG</div>
    {[
      { l: "Rüstung",       v: "1 248",   c: "var(--vg-vellum)" },
      { l: "Ausweichung",   v: "986",     c: "var(--vg-ghost-bright)" },
      { l: "Energieschild", v: "412",     c: "var(--vg-aspect-bright)" },
      { l: "Block",         v: "32%",     c: "var(--vg-vellum-warm)" },
    ].map(r => (
      <div key={r.l} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px dotted rgba(154,118,66,0.18)" }}>
        <span style={{ fontFamily: "var(--vg-serif)", fontSize: 14, color: "var(--vg-vellum-mid)" }}>{r.l}</span>
        <span style={{ fontFamily: "var(--vg-mono)", fontSize: 14, color: r.c }}>{r.v}</span>
      </div>
    ))}
  </div>
);

const ResistCard = () => {
  const res = [
    { l: "Feuer",   v: 75,  cap: 75, c: "var(--vg-blood-glow)",  glyph: "🜂" },
    { l: "Frost",   v: 68,  cap: 75, c: "var(--vg-ghost-bright)", glyph: "🜄" },
    { l: "Blitz",   v: 71,  cap: 75, c: "var(--vg-aspect-bright)", glyph: "🜁" },
    { l: "Chaos",   v: 12,  cap: 75, c: "#a060c0",  glyph: "🜍" },
  ];
  return (
    <div style={{
      border: "1px solid var(--vg-bronze-deep)", padding: 14,
      background: "rgba(8,5,3,0.5)",
    }}>
      <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)", marginBottom: 10 }}>RESISTENZEN</div>
      {res.map(r => (
        <div key={r.l} style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 10, alignItems: "center", padding: "5px 0" }}>
          <span style={{ fontFamily: "var(--vg-display)", fontSize: 14, color: r.c, width: 18, textAlign: "center" }}>{r.glyph}</span>
          <div style={{ position: "relative", height: 6, background: "#060300", border: "1px solid var(--vg-bronze-deep)" }}>
            <div style={{ width: `${(r.v/r.cap)*100}%`, height: "100%", background: `linear-gradient(90deg, ${r.c}55, ${r.c})`, boxShadow: `0 0 6px ${r.c}88` }}/>
            <div style={{ position: "absolute", right: 0, top: -2, bottom: -2, width: 1, background: "var(--vg-bronze-warm)" }}/>
          </div>
          <span style={{ fontFamily: "var(--vg-mono)", fontSize: 12, color: r.c, minWidth: 56, textAlign: "right" }}>{r.v} / {r.cap}%</span>
        </div>
      ))}
    </div>
  );
};

// -------------------------------------------------------------------------
// RIGHT — BAG PAGE (grid + item description)
// -------------------------------------------------------------------------

const BagPage = () => {
  const items = makeBagItems();
  return (
    <div style={{ display: "grid", gridTemplateRows: "auto 1fr auto", gap: 16, height: "100%" }}>
      {/* Inventory grid */}
      <div>
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8,
        }}>
          <div style={{ fontFamily: "var(--vg-display)", fontSize: 12, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)" }}>
            REISETASCHE
          </div>
          <div style={{ fontFamily: "var(--vg-mono)", fontSize: 11, color: "var(--vg-bronze-light)" }}>
            48 / 60 · 4 320 g
          </div>
        </div>

        <div style={{
          position: "relative",
          padding: 10,
          background: "rgba(10,7,3,0.5)",
          border: "1px solid var(--vg-bronze-deep)",
          boxShadow: "inset 0 0 24px rgba(0,0,0,0.7)",
        }}>
          {/* corners */}
          <div style={{ position:"absolute", top:-2, left:-2 }}><OrnamentCorner size={22} rotate={0}/></div>
          <div style={{ position:"absolute", top:-2, right:-2 }}><OrnamentCorner size={22} rotate={90}/></div>
          <div style={{ position:"absolute", bottom:-2, right:-2 }}><OrnamentCorner size={22} rotate={180}/></div>
          <div style={{ position:"absolute", bottom:-2, left:-2 }}><OrnamentCorner size={22} rotate={270}/></div>

          <div style={{
            display: "grid", gridTemplateColumns: "repeat(12, 1fr)", gap: 3,
          }}>
            {items.map((it, i) => <BagCell key={i} {...it}/>)}
          </div>
        </div>

        {/* tabs row */}
        <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
          {[
            { l: "Reisetasche", active: true },
            { l: "Erinnerungssteine", count: 12 },
            { l: "Pakt-Steine", count: 4 },
            { l: "Tinte & Tinkturen", count: 8 },
            { l: "Mahnmale", count: 17 },
            { l: "Kuriositäten", count: 23 },
          ].map((t, i) => (
            <button key={i} style={{
              padding: "6px 12px",
              background: t.active ? "linear-gradient(180deg, #2a1a10, #1a0e08)" : "transparent",
              border: `1px solid ${t.active ? "var(--vg-aspect)" : "var(--vg-bronze-deep)"}`,
              color: t.active ? "var(--vg-aspect-halo)" : "var(--vg-bronze-warm)",
              fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.22em",
              textTransform: "uppercase", cursor: "pointer",
            }}>
              {t.l} {t.count && <span style={{ fontFamily: "var(--vg-mono)", marginLeft: 4, opacity: 0.7 }}>·{t.count}</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Item description scroll */}
      <ItemTooltip/>

      {/* Currency rail */}
      <CurrencyRail/>
    </div>
  );
};

const makeBagItems = () => {
  const grid = Array.from({ length: 60 }, () => null);
  const place = (idx, w, h, item) => { grid[idx] = { ...item, w, h, anchor: true }; };
  place(0, 2, 2, { kind: "tome", rarity: "unique", name: "Liber Ardens" });
  place(2, 1, 1, { kind: "ring", rarity: "rare", name: "Asch-Ring" });
  place(3, 1, 1, { kind: "ring", rarity: "magic", name: "Schmaler Reif" });
  place(4, 2, 1, { kind: "belt", rarity: "rare", name: "Asch-Gurt" });
  place(6, 1, 2, { kind: "flask", rarity: "magic", name: "Lebenstinktur" });
  place(7, 1, 2, { kind: "flask", rarity: "magic", name: "Geistestinktur" });
  place(8, 1, 1, { kind: "sigil", rarity: "rare", name: "Sigil des Brandes" });
  place(9, 1, 1, { kind: "sigil", rarity: "magic", name: "Salz-Sigil" });
  place(10, 1, 1, { kind: "gem", rarity: "unique", name: "Stein VIII", glyph: true });
  place(11, 1, 1, { kind: "gem", rarity: "rare",   name: "Stein V" });
  place(12, 1, 1, { kind: "gem", rarity: "rare",   name: "Stein VI" });
  place(13, 1, 1, { kind: "gem", rarity: "magic",  name: "Stein III" });
  place(14, 2, 1, { kind: "scroll", rarity: "common", name: "Echo-Schriftrolle" });
  place(16, 1, 1, { kind: "amulet", rarity: "rare", name: "Anhänger des Falsch-Wortes" });
  place(17, 1, 1, { kind: "amulet", rarity: "magic", name: "Geist-Anhänger" });
  place(18, 1, 2, { kind: "helm", rarity: "rare", name: "Aschen-Kapuze II" });
  place(19, 1, 1, { kind: "gloves", rarity: "magic", name: "Schmiede-Handschuhe" });
  place(20, 1, 1, { kind: "boots", rarity: "common", name: "Wanderschuhe" });
  place(21, 1, 1, { kind: "gem", rarity: "mythic", name: "Pakt-Stein" });
  place(24, 2, 2, { kind: "robe", rarity: "unique", name: "Asche-Robe" });
  place(26, 1, 1, { kind: "ring", rarity: "magic", name: "Salzring" });
  place(27, 1, 1, { kind: "gem", rarity: "magic", name: "Whisper-Splitter" });
  place(28, 1, 1, { kind: "gem", rarity: "magic", name: "Whisper-Splitter" });
  place(29, 1, 1, { kind: "gem", rarity: "common", name: "Roher Shard" });
  place(36, 2, 1, { kind: "staff", rarity: "rare", name: "Lange Rute" });
  place(40, 1, 1, { kind: "sigil", rarity: "common", name: "Holzbrosche" });

  // mark non-anchor occupied cells transparent so they don't render
  for (let i = 0; i < grid.length; i++) {
    const it = grid[i];
    if (it && it.anchor) {
      for (let dx = 0; dx < it.w; dx++) for (let dy = 0; dy < it.h; dy++) {
        if (!(dx === 0 && dy === 0)) {
          const j = i + dx + dy*12;
          if (j !== i && grid[j] === null) grid[j] = { covered: true };
        }
      }
    }
  }
  return grid;
};

const BagCell = ({ kind, rarity, name, w = 1, h = 1, anchor, covered, glyph }) => {
  if (covered) return null;
  const rarityColor = {
    common: "var(--vg-vellum-mid)",
    magic: "var(--vg-ghost-bright)",
    rare: "var(--vg-gold-bright)",
    unique: "#c9742a",
    mythic: "var(--vg-blood-glow)",
  }[rarity];
  const empty = !kind;
  if (empty) {
    return (
      <div style={{
        aspectRatio: "1", background: "rgba(10,7,3,0.55)",
        border: "1px solid var(--vg-bronze-deep)",
        boxShadow: "inset 0 0 8px rgba(0,0,0,0.6)",
      }}/>
    );
  }
  return (
    <div style={{
      gridColumn: `span ${w}`, gridRow: `span ${h}`,
      position: "relative", aspectRatio: w === h ? "1" : undefined,
      minHeight: h * 60,
      background: "linear-gradient(160deg, #0c0704, #1c1208 60%, #050200)",
      border: `1px solid ${rarityColor}`,
      boxShadow: `inset 0 0 12px rgba(0,0,0,0.8), 0 0 6px ${rarityColor}33`,
      display: "grid", placeItems: "center",
      color: rarityColor,
    }}>
      <span style={{ position:"absolute", top:-2, left:-2, width:4, height:4, background: rarityColor }}/>
      <span style={{ position:"absolute", top:-2, right:-2, width:4, height:4, background: rarityColor }}/>
      <span style={{ position:"absolute", bottom:-2, left:-2, width:4, height:4, background: rarityColor }}/>
      <span style={{ position:"absolute", bottom:-2, right:-2, width:4, height:4, background: rarityColor }}/>
      <ItemIcon kind={kind} size={Math.min(w, h) * 48 + 8} color={rarityColor}/>
      {/* stack count for gems */}
      {glyph && (
        <span style={{
          position: "absolute", top: 2, right: 4,
          fontFamily: "var(--vg-display)", fontSize: 9, color: "var(--vg-aspect-halo)",
        }}>VIII</span>
      )}
    </div>
  );
};

const ItemTooltip = () => (
  <div style={{
    position: "relative",
    background: `
      radial-gradient(ellipse 100% 80% at 50% 0%, rgba(60,40,20,0.55), transparent 60%),
      linear-gradient(180deg, rgba(28,18,10,0.92), rgba(8,5,3,0.95))
    `,
    border: "1px solid #c9742a",
    boxShadow: "inset 0 0 30px rgba(0,0,0,0.7), 0 0 20px rgba(201,116,42,0.25)",
    padding: "18px 22px",
  }}>
    {/* corner studs */}
    <span style={{ position:"absolute", top:-3, left:-3, width:7, height:7, background: "#c9742a" }}/>
    <span style={{ position:"absolute", top:-3, right:-3, width:7, height:7, background: "#c9742a" }}/>
    <span style={{ position:"absolute", bottom:-3, left:-3, width:7, height:7, background: "#c9742a" }}/>
    <span style={{ position:"absolute", bottom:-3, right:-3, width:7, height:7, background: "#c9742a" }}/>

    {/* eyebrow */}
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
      <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.35em", color: "#c9742a" }}>UNIQUE · STAB · STUFE 42</div>
      <div style={{ fontFamily: "var(--vg-mono)", fontSize: 10, color: "var(--vg-bronze-warm)" }}>angewendet · 2/3 Sockel</div>
    </div>

    {/* name */}
    <div style={{
      fontFamily: "var(--vg-display)", fontSize: 28, fontWeight: 800, letterSpacing: "0.16em",
      color: "#dba360", textShadow: "0 0 16px rgba(201,116,42,0.55), 0 2px 0 #000",
      marginTop: 2,
    }}>STAB DES HOHLEN WORTES</div>
    <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", color: "var(--vg-bronze-warm)", fontSize: 14 }}>
      „Im-Nesh-getragen" · Glasgoldenes Zeitalter
    </div>

    <OrnamentDivider width={520} color="var(--vg-bronze)"/>

    {/* stats two-column */}
    <div style={{
      display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 28px", marginTop: 10,
    }}>
      <StatLine label="Zauberschaden"           value="+184"  pct="(+96%)" tone="implicit"/>
      <StatLine label="Krit-Chance"             value="9.6%"  pct="(+2.4%)" tone="implicit"/>
      <StatLine label="Zaubergeschwindigkeit"   value="+18%"  tone="explicit"/>
      <StatLine label="Intellekt"               value="+82"   tone="explicit"/>
      <StatLine label="Feuer-Skills entzünden Feinde immer" value="" tone="explicit-text"/>
      <StatLine label="Beschworene Geister halten 2.5s länger" value="" tone="explicit-text"/>
      <StatLine label="—— Wenn du einen Aspekt-Pakt brichst" value="" tone="corrupted"/>
      <StatLine label="—— erinnern sich Feinde nicht an deinen Angriff" value="" tone="corrupted"/>
    </div>

    {/* flavour quote */}
    <div style={{
      marginTop: 14, padding: 12,
      borderTop: "1px solid var(--vg-bronze-deep)",
      fontFamily: "var(--vg-serif)", fontStyle: "italic",
      color: "var(--vg-vellum-mid)", fontSize: 13, lineHeight: 1.5,
      textAlign: "center",
    }}>
      <span style={{ color: "var(--vg-bronze-warm)" }}>—— </span>
      „Sie schrieb dreitausend Namen in das Holz. Dann brannte sie sie aus, einen nach dem anderen. Das letzte Wort blieb hohl."
      <span style={{ color: "var(--vg-bronze-warm)" }}> ——</span>
    </div>

    {/* sockets row */}
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 12 }}>
      <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.3em", color: "var(--vg-bronze-warm)" }}>SOCKEL</div>
      <SocketChip kind="fire" filled glyph="Feuerball VII"/>
      <SocketChip kind="cold" filled glyph="Frostsalve IV"/>
      <SocketChip kind="empty"/>
    </div>

    {/* actions */}
    <div style={{
      display: "flex", gap: 10, marginTop: 12, fontFamily: "var(--vg-display)",
      fontSize: 10, letterSpacing: "0.22em", color: "var(--vg-bronze-warm)",
    }}>
      <span style={{ border: "1px solid var(--vg-bronze)", padding: "5px 12px", color: "var(--vg-aspect-halo)" }}>[F] ABLEGEN</span>
      <span style={{ border: "1px solid var(--vg-bronze-deep)", padding: "5px 12px" }}>[L] LESEN</span>
      <span style={{ border: "1px solid var(--vg-bronze-deep)", padding: "5px 12px" }}>[X] SCHMIEDE</span>
      <span style={{ border: "1px solid var(--vg-bronze-deep)", padding: "5px 12px" }}>[B] BRENNEN</span>
    </div>
  </div>
);

const StatLine = ({ label, value, pct, tone }) => {
  const color = {
    implicit: "var(--vg-vellum-warm)",
    explicit: "var(--vg-ghost-bright)",
    "explicit-text": "var(--vg-ghost-bright)",
    corrupted: "var(--vg-blood-glow)",
  }[tone];
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12,
      padding: "3px 0", borderBottom: "1px dotted rgba(154,118,66,0.18)",
    }}>
      <span style={{
        fontFamily: tone === "explicit-text" || tone === "corrupted" ? "var(--vg-serif)" : "var(--vg-serif)",
        fontStyle: tone === "corrupted" ? "italic" : "normal",
        fontSize: 13, color,
      }}>{label}</span>
      {value && (
        <span style={{ fontFamily: "var(--vg-mono)", fontSize: 13, color }}>
          {value} <span style={{ color: "var(--vg-bronze-warm)", fontSize: 11 }}>{pct}</span>
        </span>
      )}
    </div>
  );
};

const SocketChip = ({ kind, filled, glyph }) => {
  const accent = filled
    ? { fire: "var(--vg-blood-glow)", cold: "var(--vg-ghost-bright)", lightning: "var(--vg-aspect-bright)" }[kind] || "var(--vg-aspect-bright)"
    : "var(--vg-bronze-deep)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{
        width: 22, height: 22,
        background: filled ? `radial-gradient(circle, ${accent} 0%, #050200 80%)` : "rgba(10,7,3,0.6)",
        border: `1px solid ${accent}`,
        boxShadow: filled ? `0 0 6px ${accent}` : "none",
        transform: "rotate(45deg)",
      }}/>
      {filled && <span style={{ fontFamily: "var(--vg-display)", fontSize: 9, color: accent, letterSpacing: "0.15em" }}>{glyph}</span>}
      {!filled && <span style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 11, color: "var(--vg-bronze-warm)" }}>frei</span>}
    </div>
  );
};

const CurrencyRail = () => {
  const c = [
    { l: "Asche",          v: "12 480", c: "var(--vg-vellum-warm)", g: "✚" },
    { l: "Gold-Tropfen",   v: "284",    c: "var(--vg-gold-bright)", g: "❂" },
    { l: "Erinnerungs-Tinte", v: "47",  c: "var(--vg-ghost-bright)", g: "⌖" },
    { l: "Pakt-Wachs",     v: "8",      c: "var(--vg-blood-glow)", g: "✥" },
    { l: "Knochenstaub",   v: "126",    c: "#cfb98a", g: "❀" },
  ];
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", gap: 10,
      padding: "8px 14px",
      background: "rgba(10,7,3,0.5)",
      border: "1px solid var(--vg-bronze-deep)",
    }}>
      {c.map(x => (
        <div key={x.l} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            width: 28, height: 28, display: "grid", placeItems: "center",
            background: "rgba(10,7,3,0.7)", border: `1px solid ${x.c}`,
            color: x.c, fontSize: 18, boxShadow: `0 0 6px ${x.c}44`,
          }}>{x.g}</span>
          <div>
            <div style={{ fontFamily: "var(--vg-display)", fontSize: 8, letterSpacing: "0.25em", color: "var(--vg-bronze-warm)" }}>{x.l.toUpperCase()}</div>
            <div style={{ fontFamily: "var(--vg-mono)", fontSize: 14, color: x.c }}>{x.v}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

window.InventoryScreen = InventoryScreen;
