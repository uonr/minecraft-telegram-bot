{
  description = "Minecraft Telegram Bot";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs?ref=nixpkgs-unstable";
    utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, utils }: (utils.lib.eachSystem [ "x86_64-linux" ] (system:
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
    pythonEnv = pkgs.python3.withPackages(packages: with packages; [
      python-telegram-bot python-dotenv mcrcon
    ]);
    minecraft-telegram-bot = with pkgs.python3Packages; buildPythonPackage {
      pname = "minecraft-telegram-bot";
      version = "1.0";
      propagatedBuildInputs = [ python-telegram-bot python-dotenv mcrcon ];
      src = ./.;
    };
  in {
    packages = {
      pythonEnv = pythonEnv;
      minecraft-telegram-bot =  minecraft-telegram-bot;
    };
    defaultApp = utils.lib.mkApp {
      drv = minecraft-telegram-bot;
      exePath = "/bin/bot.py";
    };
    defaultPackage = minecraft-telegram-bot; # If you want to juist build the environment
    devShell = pythonEnv.env; # We need .env in order to use `nix develop`
  }));
}
