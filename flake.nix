{
  description = "bridge between in telegram and minecraft";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs";
    utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, utils }: utils.lib.eachDefaultSystem (system: 
  let 
    pkgs = nixpkgs.legacyPackages.${system};

    mcrcon = pkgs.python3Packages.buildPythonPackage rec {
      pname = "mcrcon";
      version = "0.7.0";
      src = pkgs.python3Packages.fetchPypi {
        inherit pname version;
        sha256 = "wvHK8kZ+KD4MzSQ28c4h8EJCsDxfr7OGDjkk12SpENQ=";
      };
    };
    minecraft-telegram-bot = with pkgs.python3Packages; buildPythonPackage {
      pname = "minecraft-telegram-bot";
      version = "1.0";
      propagatedBuildInputs = [ python-telegram-bot python-dotenv mcrcon ];
      src = ./.;
    };
    python = pkgs.python3.withPackages(ps: [ minecraft-telegram-bot ]);
  in {
    overlay = prev: self: {
      inherit minecraft-telegram-bot;
    };
    packages = {
      inherit minecraft-telegram-bot;
    };
    defaultApp = utils.lib.mkApp {
      drv = minecraft-telegram-bot;
      exePath = "/bin/bot.py";
    };
    nixosModule = { config, lib, ... }:
    with lib;
    let 
      cfg = config.services.minecraft-telegram-bot;
    in {
      options = {
        services.minecraft-telegram-bot = {
          enable = mkEnableOption "enable minecraft telegram bot service";
          logFilePath = mkOption { type = types.str; };
          chatTitle = mkOption { type = types.str; };
          environmentFile = mkOption { type = types.str; };
        };
      };
      config = mkIf cfg.enable {
        systemd.services.minecraft-telegram-bot = {
          enable = true;
          after = [ "network-online.target" ];
          wants = [ "network-online.target" ];
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            Type = "simple";
            User = "root";
            Group = "root";
            MemoryMax = "128M";
            EnvironmentFile = cfg.environmentFile;
            Restart = "always";
            RestartSec = "3s";
          };
          environment = {
            CHAT_TITLE = cfg.chatTitle;
            LOG_FILE_PATH = cfg.logFilePath;
          };
          script = "${minecraft-telegram-bot}/bin/bot.py";
          preStop = "${minecraft-telegram-bot}/bin/bot.py stopped";
        };
      };
    };
    defaultPackage = minecraft-telegram-bot;
    devShell = python.env;
  });
}
