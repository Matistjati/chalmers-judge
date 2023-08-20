{ pkgs }:
let
  python3-omogenjudge = pkgs.poetry2nix.mkPoetryApplication {
    projectDir = builtins.filterSource
      (path: type: type != "directory" || baseNameOf path != "nix") ./..;

    overrides = pkgs.poetry2nix.defaultPoetryOverrides.extend (final: prev: {
      mailjet-rest = prev.mailjet-rest.overridePythonAttrs (old: {
        buildInputs = (old.buildInputs or [ ]) ++ [ prev.setuptools ];
      });
      plastex = prev.plastex.overridePythonAttrs (old: {
        buildInputs = (old.buildInputs or [ ]) ++ [ prev.setuptools ];
      });
      types-oauthlib = prev.types-oauthlib.overridePythonAttrs (old: {
        buildInputs = (old.buildInputs or [ ]) ++ [ prev.setuptools ];
      });
      uwsgi = prev.uwsgi.overridePythonAttrs (old: {
        buildInputs = (old.buildInputs or [ ]) ++ [ prev.setuptools ];
      });

      problemtools = prev.problemtools.overridePythonAttrs (old: {
        buildInputs = (old.buildInputs or [ ])
          ++ [ prev.setuptools pkgs.gmp pkgs.boost ];
        nativeBuildInputs = (old.nativeBuildInputs or [ ])
          ++ [ pkgs.automake pkgs.autoconf ];
      });

      cryptography = prev.cryptography.overridePythonAttrs (old: {
        cargoDeps = pkgs.rustPlatform.fetchCargoTarball {
          src = old.src;
          sourceRoot = "${old.pname}-${old.version}/src/rust";
          name = "${old.pname}-${old.version}";
          sha256 = "sha256-0x+KIqJznDEyIUqVuYfIESKmHBWfzirPeX2R/cWlngc=";
        };
      });
    });
  };

  frontend_assets = pkgs.buildNpmPackage {
    pname = "omogenjudge";
    version = "1.0.0";
    # Skip the scripts
    src = builtins.filterSource
      (path: type: type == "directory" || baseNameOf path != ".sh")
      ../frontend_assets;
    npmDepsHash = "sha256-zoQr55XuVrsLIfQA6DeBJYsVpN2+/5Mt7uYp5XaBM20=";
    PYTHON =
      "${pkgs.python3.withPackages (p: [ p.distutils_extra ])}/bin/python3";
  };

  omogenjudge-web = pkgs.stdenv.mkDerivation {
    name = "omogenjudge-web";
    src = ../.;
    buildInputs = [
      frontend_assets
      pkgs.bash
      pkgs.nodejs_18
      pkgs.poetry
      python3-omogenjudge
    ];
    buildPhase = ''
      patchShebangs .
      ./packaging/build-web.sh
    '';
  };

  omogenjudge-queue = pkgs.runCommand "omogenjudge-queue" { } ''
    ${../.}/packaging/build-queue.sh
  '';
  omogenjudge-host = pkgs.runCommand "omogenjudge-host" { } ''
    ${../.}/packaging/build-host.sh
  '';
in { inherit omogenjudge-web omogenjudge-queue omogenjudge-host; }
