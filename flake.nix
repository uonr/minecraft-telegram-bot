{
  description = "Minecraft Telegram Bot";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        pythonPackages =
          ps:
          with ps;
          (
            [
              setuptools
              python-telegram-bot
              python-dotenv
              black
              httpx
              aio-mc-rcon
            ]
            ++ python-telegram-bot.optional-dependencies.job-queue
          );

        bot = pkgs.python3Packages.buildPythonApplication {
          pname = "minecraft-telegram-bot";
          version = "0.1.0";
          src = ./.;
          propagatedBuildInputs = (pythonPackages pkgs.python3.pkgs);
          nativeBuildInputs = [ pkgs.pkg-config ];
          PKG_CONFIG_PATH = "${pkgs.openssl.dev}/lib/pkgconfig";
        };

        aio-mc-rcon = pkgs.python3Packages.buildPythonPackage rec {
          pname = "aio-mc-rcon";
          version = "3.4.1";
          format = "pyproject";
          nativeBuildInputs = [
            pkgs.python3Packages.poetry-core
          ];
          src = pkgs.fetchPypi {
            pname = "aio_mc_rcon";

            inherit version;
            sha256 = "sha256-wWI+1UpWswKr12p76fvqsSdShb9Y+BCaeBafgsAc3RM=";
          };
        };
      in
      {
        packages.default = bot;

        apps.default = {
          type = "app";
          program = "${bot}/bin/minecraft-telegram-bot";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            (pkgs.python3.withPackages pythonPackages)
          ];
          nativeBuildInputs = [ pkgs.pkg-config ];
          PKG_CONFIG_PATH = "${pkgs.openssl.dev}/lib/pkgconfig";
        };
      }
    );
}
