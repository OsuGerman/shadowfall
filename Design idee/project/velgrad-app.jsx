/* global React, ReactDOM, DesignCanvas, DCSection, DCArtboard, HudScreen, InventoryScreen, SkillTreeScreen, DeathScreen, TweaksPanel, useTweaks, TweakSection, TweakSelect, TweakRadio, TweakColor, TweakToggle, TweakSlider */

// =========================================================================
// VELGRAD — App composer (design canvas + tweaks)
// =========================================================================

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "aspect": "valsa",
  "breathing": true,
  "ornamentDensity": "rich"
}/*EDITMODE-END*/;

const ASPECT_OPTIONS = [
  "valsa", "kharn", "nheyra", "ousen", "shulavh", "hollow"
];
const ASPECT_LABELS = {
  valsa:   "Valsa — Wille (Feuer · Gold)",
  kharn:   "Kharn — Form (Bronze · Stein)",
  nheyra:  "Nheyra — Zeit (Stahlblau · Spiegel)",
  ousen:   "Ousen — Geist (Geist-Cyan · Auge)",
  shulavh: "Shulavh — Bindung (Purpur · Faden)",
  hollow:  "??? — Vergessen (Hohl · Asche)",
};

const App = () => {
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);

  // Apply aspect to the whole document
  React.useEffect(() => {
    document.documentElement.setAttribute("data-aspect", tweaks.aspect);
    document.documentElement.style.setProperty("--vg-breathe", tweaks.breathing ? "6200ms" : "0ms");
  }, [tweaks.aspect, tweaks.breathing]);

  return (
    <>
      <DesignCanvas
        title="Codex Velgradensis — UI Studien"
        subtitle="Vier diegetische Tafeln aus dem Codex Sartum · 814 N.D.V."
        accent="#c89827"
        background="radial-gradient(ellipse at 50% 30%, #1a0c06 0%, #0a0604 40%, #050200 100%)"
      >
        <DCSection id="hud" title="Tafel I — Im Gefecht (HUD)" subtitle="Aschenfelder · Glas-Pass · während des Falls von Vosshem">
          <DCArtboard id="hud-1" label="HUD · 1920×1080" width={1920} height={1080} background="#000">
            <HudScreen aspect={tweaks.aspect}/>
          </DCArtboard>
        </DCSection>

        <DCSection id="inventory" title="Tafel II — Das Inventar" subtitle="Codex Sartum, Folio CXII recto · Die Ausrüstung der Funkengeborenen">
          <DCArtboard id="inv-1" label="Inventar · Buchspread" width={1760} height={1100} background="#0a0604">
            <InventoryScreen aspect={tweaks.aspect}/>
          </DCArtboard>
        </DCSection>

        <DCSection id="tree" title="Tafel III — Der Erinnerungs-Baum" subtitle="Folio CCXLVII · 67 Erinnerungen vergeben, drei Keystones beschritten">
          <DCArtboard id="tree-1" label="Skill-Tree · Erinnerungsweb" width={1760} height={1100} background="#0a0604">
            <SkillTreeScreen aspect={tweaks.aspect}/>
          </DCArtboard>
        </DCSection>

        <DCSection id="death" title="Tafel IV — Der Vergangene" subtitle="Memorialtafel · ein Tod an der Aschwunde">
          <DCArtboard id="death-1" label="Death-Screen · 1920×1080" width={1920} height={1080} background="#000">
            <DeathScreen aspect={tweaks.aspect}/>
          </DCArtboard>
        </DCSection>
      </DesignCanvas>

      <TweaksPanel title="Velgrad — Tafel-Tweaks">
        <TweakSection title="Aspekt-Bindung" subtitle="Wechsle die Akzentfarbe + Glyphe zum gewählten Aspekt">
          <TweakSelect
            value={tweaks.aspect}
            onChange={(v) => setTweak("aspect", v)}
            options={ASPECT_OPTIONS.map(v => ({ value: v, label: ASPECT_LABELS[v] }))}
          />
        </TweakSection>
        <TweakSection title="Atemzug" subtitle="Sanftes Pulsieren der Glyphen, Embers, Flammen">
          <TweakToggle value={tweaks.breathing} onChange={(v) => setTweak("breathing", v)} label="Atem aktiv"/>
        </TweakSection>
      </TweaksPanel>
    </>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
