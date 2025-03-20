let
  # https://wiki.nixos.org/wiki/Python
  pkgs = import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/nixos-24.11.tar.gz") { };
in
pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (
      python-pkgs: with python-pkgs; [
        pip
        setuptools
        wheel
      ]
    ))
  ];
  shellHook = ''
  '';
}
