with import <nixpkgs> {};
with python38Packages;
let
  mcrcon = buildPythonPackage rec {
    pname = "mcrcon";
    version = "0.7.0";
    src = pkgs.python3.pkgs.fetchPypi {
      inherit pname version;
      sha256 = "wvHK8kZ+KD4MzSQ28c4h8EJCsDxfr7OGDjkk12SpENQ=";
    };
  };
  python = pkgs.python38.withPackages (pythonPkg: with pythonPkg; [ python-telegram-bot python-dotenv mcrcon ]);
in
mkShell {
  buildInputs = [ python ];
}
