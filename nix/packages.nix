{ lib, pkgs }:
let
  python3-omogenjudge = pkgs.poetry2nix.mkPoetryApplication {
    # Skip the nix/ directory
    projectDir =
      builtins.filterSource (path: type: baseNameOf path != "nix") ./..;

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
      (path: type: type == "directory" || !(lib.strings.hasSuffix ".sh" path))
      ../frontend_assets;
    npmDepsHash = "sha256-zoQr55XuVrsLIfQA6DeBJYsVpN2+/5Mt7uYp5XaBM20=";
    PYTHON =
      "${pkgs.python3.withPackages (p: [ p.distutils_extra ])}/bin/python3";

    #nativeBuildInputs = [ pkgs.tree ];
      #tree --filelimit 20
    installPhase = ''
      mkdir $out
      cp -r static/* $out/
      cp -r img $out/
    '';
  };

  omogen_config_file = pkgs.writeText "web.toml" ''
    [web]
    secret_key = "secret_key placeholder"

    [email]
    mailjet_api_key = "mailjet_api_key placeholder"
    mailjet_api_secret = "mailjet_api_secret placeholder"

    [database]
    password = "password placeholder"
  '';

  omogenjudge-web = pkgs.stdenv.mkDerivation {
    name = "omogenjudge-web";
    src = ../.;
    nativeBuildInputs = [
      pkgs.bash
      pkgs.nodejs_18
      pkgs.poetry
      python3-omogenjudge
    ];
    buildPhase = ''
      set -v
      patchShebangs .

      mkdir output
      cp -r ${frontend_assets} output/frontend_assets

      OMOGEN_CONFIG_FILE_PATH=${omogen_config_file} \
      PRODUCTION=1 \
      python manage.py collectstatic -c --no-input
    '';
    installPhase = ''
      cp -r packaging/web/ $out/
      cp -r omogenjudge $out/
      cp -r bin $out/
      cp pyproject.toml $out/
      cp -r output/static $out/
    '';
  };

  omogenjudge-queue = pkgs.runCommand "omogenjudge-queue" { } ''
    ${../.}/packaging/build-queue.sh
  '';
  omogenjudge-host = pkgs.runCommand "omogenjudge-host" { } ''
    ${../.}/packaging/build-host.sh
  '';
in { inherit python3-omogenjudge frontend_assets omogenjudge-web omogenjudge-queue omogenjudge-host; }
