{ lib, pkgs }:
let
  python3-omogenjudge-attrset = {
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
  python3-omogenjudge-application =
    pkgs.poetry2nix.mkPoetryApplication python3-omogenjudge-attrset;
  python3-omogenjudge-env =
    pkgs.poetry2nix.mkPoetryEnv python3-omogenjudge-attrset;
  python3-omogenjudge-deps = (pkgs.poetry2nix.mkPoetryPackages
    python3-omogenjudge-attrset).poetryPackages;
  test-thingy = pkgs.poetry2nix.mkPoetryEnv (python3-omogenjudge-attrset // {
    extraPackages = _: [ python3-omogenjudge-application ];
  });

  # This is a weird workaround around poetry2nix being weird (not supporting running script from a
  # dependency in the library context of the project).
  django-admin = let
    find-django =
      lib.lists.findFirst (drv: drv.pname == "django") (throw "missing django");
    django = find-django python3-omogenjudge-deps;
  in pkgs.writeShellScriptBin "django-admin" ''
    NIX_PYTHONPREFIX=${python3-omogenjudge-env} \
    NIX_PYTHONEXECUTABLE=${python3-omogenjudge-env}/bin/python3.10 \
    NIX_PYTHONPATH=.:${python3-omogenjudge-env}/lib/python3.10/site-packages \
    PYTHONNOUSERSITE=true ${django}/bin/django-admin "$@"
  '';

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

  omogenjudge-web-static = pkgs.stdenv.mkDerivation {
    name = "omogenjudge-web-static";
    # Skip the nix/ directory
    src = builtins.filterSource (path: type: baseNameOf path != "nix") ./..;
    nativeBuildInputs = [ pkgs.bash pkgs.nodejs_18 python3-omogenjudge-env ];
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
      mkdir $out
      cp -r output/static/* $out/
    '';
  };

  omogenjudge-impure-bazel-build = let
    omogenjudge-host-src =
      builtins.filterSource (path: type: baseNameOf path != ".bazelversion")
      ../judgehost;
    omogenjudge-host-build-script = pkgs.writeShellApplication {
      name = "build-script";
      runtimeInputs = let p = pkgs; in [ p.bash p.coreutils p.bazel_5 ];
      text = ''
        echo NOTE: Bazel may break on ipv6-only networks
        set -v

        cd ${omogenjudge-host-src}
        bazel fetch //... --loading_phase_threads=1
        bazel build //...

        OUT=$(bazel info output_path)
        QUEUE_DEB="$OUT/k8-fastbuild/bin/queue/deb/omogenjudge-queue_0.0.1_amd64.deb"
        HOST_DEB="$OUT/k8-fastbuild/bin/judgehost/deb/omogenjudge-host_0.0.2_amd64.deb"

        nix store add-file --dry-run --name omogenjudge-queue.deb "$QUEUE_DEB"
        nix store add-file --name omogenjudge-queue.deb "$QUEUE_DEB" | xargs nix-store --query --hash
        nix hash file "$QUEUE_DEB"

        nix store add-file --dry-run --name omogenjudge-host.deb "$HOST_DEB"
        nix store add-file --name omogenjudge-host.deb "$HOST_DEB" | xargs nix-store --query --hash
        nix hash file "$HOST_DEB"
      '';
    };
  in pkgs.buildFHSUserEnv {
    name = "omogenjudge-host";
    runScript = "${omogenjudge-host-build-script}/bin/build-script";
    targetPkgs = p: [ p.gcc p.glibc ];
  };
  omogenjudge-host-deb = pkgs.requireFile {
    name = "omogenjudge-host.deb";
    sha256 = "sha256-oIVUeRsniTYbheMrkpZONcjY8I+jAyRVlI8PY7tQt3w=";
    message = ''
      This derivation is built impurely using bazel.
      Create it using \`nix run .#omogenjudge-impure-bazel-build\`.
    '';
  };
  omogenjudge-queue-deb = pkgs.requireFile {
    name = "omogenjudge-queue.deb";
    sha256 = "sha256-9if9npPDbD2HhC0rlXb0jSQ6A9XJ6kbyeYt63yW265U=";
    message = ''
      This derivation is built impurely using bazel.
      Create it using \`nix run .#omogenjudge-impure-bazel-build\`.
    '';
  };
  omogenjudge-host-and-queue = pkgs.runCommand "omogenjudge-host-and-queue" {
    nativeBuildInputs = [ pkgs.dpkg ];
  } ''
    mkdir host queue
    dpkg-deb -R ${omogenjudge-host-deb} host
    dpkg-deb -R ${omogenjudge-queue-deb} queue

    mkdir $out
    install -m 544 host/usr/bin/omogenjudge-host $out
    install -m 644 host/etc/systemd/system/omogenjudge-host.service $out
    install -m 644 host/etc/omogen/judgehost.toml $out

    install -m 544 queue/usr/bin/omogenjudge-queue $out
    install -m 644 queue/etc/systemd/system/omogenjudge-queue.service $out
    install -m 644 queue/etc/omogen/queue.toml $out
  '';

in {
  inherit python3-omogenjudge-application python3-omogenjudge-env django-admin
    frontend_assets omogenjudge-web-static omogenjudge-host-and-queue
    omogenjudge-impure-bazel-build test-thingy;
}
