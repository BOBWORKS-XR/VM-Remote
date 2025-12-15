#!/bin/bash
# Install Voicemeeter Deck app on Steam Deck

INSTALL_DIR="$HOME/voicemeeter-deck"
DESKTOP_FILE="$HOME/.local/share/applications/voicemeeter-deck.desktop"

echo "Installing Voicemeeter Deck..."

# Create install directory
mkdir -p "$INSTALL_DIR"

# Copy main script
cp voicemeeter_deck.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/voicemeeter_deck.py"

# Install desktop entry
mkdir -p "$HOME/.local/share/applications"
cp voicemeeter-deck.desktop "$DESKTOP_FILE"
sed -i "s|/home/deck|$HOME|g" "$DESKTOP_FILE"

echo "Done! You can find 'Voicemeeter Deck' in your app menu."
echo "Or run: python3 $INSTALL_DIR/voicemeeter_deck.py"
