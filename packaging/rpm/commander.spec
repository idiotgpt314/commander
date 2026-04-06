Name:           commander
Version:        0.2.2
Release:        1%{?dist}
Summary:        Wayland overlay AI harness with voice and text control
License:        Custom
URL:            https://github.com/idiotgpt314/commander
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz

Requires:       python3
Requires:       python3-gobject
Requires:       python3-vosk
Requires:       gtk4
Requires:       libadwaita
Requires:       gtk4-layer-shell
Requires:       pipewire

%description
Commander is a local system-control harness for Linux with text and voice
launch flows, configurable AI backends, and a background trainer.

%prep
%autosetup -n commander-%{version}

%install
mkdir -p %{buildroot}/usr/lib/commander
cp -r harness_config.py system_agent.py system_agent_trainer.py scenarios.json release-targets.json config.example.json README.md VERSION packaging scripts vosk-model-small-en-us-0.15 %{buildroot}/usr/lib/commander/
install -Dm755 system-agent %{buildroot}/usr/lib/commander/system-agent
install -Dm755 system-agent-trainer %{buildroot}/usr/lib/commander/system-agent-trainer
install -Dm755 commander %{buildroot}/usr/bin/commander
install -Dm755 commander-trainer %{buildroot}/usr/bin/commander-trainer

%files
/usr/bin/commander
/usr/bin/commander-trainer
/usr/lib/commander

%changelog
* Sun Apr 06 2026 Commander Maintainer <noreply@example.com> - 0.1.2-1
- Fix packaged background startup behavior
