import {
  definePlugin,
  PanelSection,
  PanelSectionRow,
  SliderField,
  ToggleField,
  ButtonItem,
  TextField,
  staticClasses,
} from "@decky/ui";
import { callable, addEventListener, removeEventListener } from "@decky/api";
import { useState, useEffect, FC } from "react";
import { FaMicrophone, FaVolumeUp, FaCog } from "react-icons/fa";

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

const StripControl: FC<{
  index: number;
  label: string;
  state: StripState;
  onGainChange: (gain: number) => void;
  onMuteToggle: () => void;
}> = ({ index, label, state, onGainChange, onMuteToggle }) => {
  return (
    <PanelSection title={label}>
      <PanelSectionRow>
        <SliderField
          label="Volume"
          value={state.gain}
          min={-60}
          max={12}
          step={1}
          showValue={true}
          onChange={(value) => onGainChange(value)}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ToggleField
          label="Mute"
          checked={state.muted}
          onChange={onMuteToggle}
        />
      </PanelSectionRow>
    </PanelSection>
  );
};

const SettingsPanel: FC<{
  settings: Settings;
  onSave: (settings: Settings) => void;
  onTest: () => void;
  connectionStatus: string;
}> = ({ settings, onSave, onTest, connectionStatus }) => {
  const [localSettings, setLocalSettings] = useState(settings);

  return (
    <PanelSection title="VBAN Settings">
      <PanelSectionRow>
        <TextField
          label="PC IP Address"
          value={localSettings.pc_ip}
          onChange={(e) =>
            setLocalSettings({ ...localSettings, pc_ip: e.target.value })
          }
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <TextField
          label="VBAN Port"
          value={String(localSettings.vban_port)}
          onChange={(e) =>
            setLocalSettings({
              ...localSettings,
              vban_port: parseInt(e.target.value) || 6980,
            })
          }
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <TextField
          label="Stream Name"
          value={localSettings.stream_name}
          onChange={(e) =>
            setLocalSettings({ ...localSettings, stream_name: e.target.value })
          }
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => onSave(localSettings)}>
          Save Settings
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onTest}>
          Test Connection
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <div style={{ textAlign: "center", padding: "8px" }}>
          Status: {connectionStatus}
        </div>
      </PanelSectionRow>
    </PanelSection>
  );
};

const Content: FC = () => {
  const [showSettings, setShowSettings] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("Unknown");
  const [settings, setSettings] = useState<Settings>({
    pc_ip: "192.168.1.100",
    vban_port: 6980,
    stream_name: "Command1",
  });

  // Strip states (Hardware Inputs) - Voicemeeter Banana has 3 hardware + 2 virtual
  const [strips, setStrips] = useState<StripState[]>([
    { gain: 0, muted: false }, // Strip 0: Hardware Input 1
    { gain: 0, muted: false }, // Strip 1: Hardware Input 2
    { gain: 0, muted: false }, // Strip 2: Hardware Input 3
    { gain: 0, muted: false }, // Strip 3: Virtual Input 1 (VAIO)
    { gain: 0, muted: false }, // Strip 4: Virtual Input 2 (AUX)
  ]);

  // Bus states (Outputs)
  const [buses, setBuses] = useState<StripState[]>([
    { gain: 0, muted: false }, // Bus 0: A1
    { gain: 0, muted: false }, // Bus 1: A2
    { gain: 0, muted: false }, // Bus 2: A3
    { gain: 0, muted: false }, // Bus 3: B1
    { gain: 0, muted: false }, // Bus 4: B2
  ]);

  useEffect(() => {
    // Load settings on mount
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

  const handleSaveSettings = async (newSettings: Settings) => {
    setSettings(newSettings);
    await saveSettings(newSettings);
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

  const stripLabels = [
    "🎤 Hardware 1",
    "🎤 Hardware 2",
    "🎤 Hardware 3",
    "🎵 Virtual 1",
    "🎵 Virtual 2",
  ];

  const busLabels = ["🔊 A1", "🔊 A2", "🔊 A3", "🔊 B1", "🔊 B2"];

  return (
    <div>
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
        <SettingsPanel
          settings={settings}
          onSave={handleSaveSettings}
          onTest={handleTestConnection}
          connectionStatus={connectionStatus}
        />
      )}

      <PanelSection title="Inputs (Strips)">
        {strips.map((strip, index) => (
          <StripControl
            key={`strip-${index}`}
            index={index}
            label={stripLabels[index]}
            state={strip}
            onGainChange={(gain) => handleStripGainChange(index, gain)}
            onMuteToggle={() => handleStripMuteToggle(index)}
          />
        ))}
      </PanelSection>

      <PanelSection title="Outputs (Buses)">
        {buses.map((bus, index) => (
          <StripControl
            key={`bus-${index}`}
            index={index}
            label={busLabels[index]}
            state={bus}
            onGainChange={(gain) => handleBusGainChange(index, gain)}
            onMuteToggle={() => handleBusMuteToggle(index)}
          />
        ))}
      </PanelSection>
    </div>
  );
};

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
