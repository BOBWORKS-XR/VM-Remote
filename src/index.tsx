import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  SliderField,
  ToggleField,
  TextField,
  staticClasses,
} from "@decky/ui";
import {
  callable,
  definePlugin,
} from "@decky/api";
import { useState, useEffect } from "react";
import { FaVolumeUp, FaCog } from "react-icons/fa";

// Python backend callables
const getSettings = callable<[], Settings>("get_settings");
const saveSettings = callable<[Settings], void>("save_settings");
const setStripParam = callable<[number, string, number], boolean>("set_strip_param");
const setBusParam = callable<[number, string, number], boolean>("set_bus_param");
const toggleStripMute = callable<[number], boolean>("toggle_strip_mute");
const toggleBusMute = callable<[number], boolean>("toggle_bus_mute");
const testConnection = callable<[], boolean>("test_connection");

interface Settings {
  pc_ip: string;
  vban_port: number;
  stream_name: string;
}

interface StripState {
  gain: number;
  muted: boolean;
}

function Content() {
  const [showSettings, setShowSettings] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("Unknown");
  const [settings, setSettings] = useState<Settings>({
    pc_ip: "192.168.1.100",
    vban_port: 6980,
    stream_name: "Command1",
  });

  const [strips, setStrips] = useState<StripState[]>([
    { gain: 0, muted: false },
    { gain: 0, muted: false },
    { gain: 0, muted: false },
    { gain: 0, muted: false },
    { gain: 0, muted: false },
  ]);

  const [buses, setBuses] = useState<StripState[]>([
    { gain: 0, muted: false },
    { gain: 0, muted: false },
    { gain: 0, muted: false },
    { gain: 0, muted: false },
    { gain: 0, muted: false },
  ]);

  useEffect(() => {
    getSettings().then(setSettings).catch(console.error);
  }, []);

  const handleStripGainChange = async (index: number, gain: number) => {
    const newStrips = [...strips];
    newStrips[index].gain = gain;
    setStrips(newStrips);
    await setStripParam(index, "Gain", gain);
  };

  const handleStripMuteToggle = async (index: number) => {
    const newStrips = [...strips];
    newStrips[index].muted = !newStrips[index].muted;
    setStrips(newStrips);
    await toggleStripMute(index);
  };

  const handleBusGainChange = async (index: number, gain: number) => {
    const newBuses = [...buses];
    newBuses[index].gain = gain;
    setBuses(newBuses);
    await setBusParam(index, "Gain", gain);
  };

  const handleBusMuteToggle = async (index: number) => {
    const newBuses = [...buses];
    newBuses[index].muted = !newBuses[index].muted;
    setBuses(newBuses);
    await toggleBusMute(index);
  };

  const handleSaveSettings = async () => {
    await saveSettings(settings);
    setConnectionStatus("Settings saved!");
  };

  const handleTestConnection = async () => {
    setConnectionStatus("Testing...");
    try {
      const result = await testConnection();
      setConnectionStatus(result ? "Connected!" : "Failed to connect");
    } catch {
      setConnectionStatus("Error testing connection");
    }
  };

  const stripLabels = ["HW 1", "HW 2", "HW 3", "Virt 1", "Virt 2"];
  const busLabels = ["A1", "A2", "A3", "B1", "B2"];

  return (
    <>
      <PanelSection>
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => setShowSettings(!showSettings)}
          >
            <FaCog /> {showSettings ? "Hide Settings" : "Show Settings"}
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>

      {showSettings && (
        <PanelSection title="VBAN Settings">
          <PanelSectionRow>
            <TextField
              label="PC IP Address"
              value={settings.pc_ip}
              onChange={(e) => setSettings({ ...settings, pc_ip: e.target.value })}
            />
          </PanelSectionRow>
          <PanelSectionRow>
            <TextField
              label="VBAN Port"
              value={String(settings.vban_port)}
              onChange={(e) => setSettings({ ...settings, vban_port: parseInt(e.target.value) || 6980 })}
            />
          </PanelSectionRow>
          <PanelSectionRow>
            <TextField
              label="Stream Name"
              value={settings.stream_name}
              onChange={(e) => setSettings({ ...settings, stream_name: e.target.value })}
            />
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={handleSaveSettings}>
              Save Settings
            </ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={handleTestConnection}>
              Test Connection
            </ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <div style={{ textAlign: "center", padding: "8px" }}>
              Status: {connectionStatus}
            </div>
          </PanelSectionRow>
        </PanelSection>
      )}

      <PanelSection title="Inputs">
        {strips.map((strip, index) => (
          <PanelSection key={`strip-${index}`} title={stripLabels[index]}>
            <PanelSectionRow>
              <SliderField
                label="Volume"
                value={strip.gain}
                min={-60}
                max={12}
                step={1}
                showValue={true}
                onChange={(value) => handleStripGainChange(index, value)}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <ToggleField
                label="Mute"
                checked={strip.muted}
                onChange={() => handleStripMuteToggle(index)}
              />
            </PanelSectionRow>
          </PanelSection>
        ))}
      </PanelSection>

      <PanelSection title="Outputs">
        {buses.map((bus, index) => (
          <PanelSection key={`bus-${index}`} title={busLabels[index]}>
            <PanelSectionRow>
              <SliderField
                label="Volume"
                value={bus.gain}
                min={-60}
                max={12}
                step={1}
                showValue={true}
                onChange={(value) => handleBusGainChange(index, value)}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <ToggleField
                label="Mute"
                checked={bus.muted}
                onChange={() => handleBusMuteToggle(index)}
              />
            </PanelSectionRow>
          </PanelSection>
        ))}
      </PanelSection>
    </>
  );
}

export default definePlugin(() => {
  console.log("Voicemeeter Deck plugin loaded!");

  return {
    name: "Voicemeeter Deck",
    titleView: <div className={staticClasses.Title}>Voicemeeter Deck</div>,
    content: <Content />,
    icon: <FaVolumeUp />,
    onDismount() {
      console.log("Voicemeeter Deck plugin unloaded!");
    },
  };
});
