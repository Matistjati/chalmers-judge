{ config, lib, pkgs, omogen-python-deps, ... }:
let
  cfg = {
    var-lib-omogen = "/var/lib/omogen";
    userweb = "omogen-web";
    group = "omogen";
    uwsgi-socket = "127.0.0.1:62542";
  };
in {
  users.users = {
    root = {
      password = " ";
      packages = [ pkgs.pkgsOmogen.django-admin ];
    };
    omogen-web = {
      isSystemUser = true;
      group = cfg.group;
    };
  };
  users.groups.${cfg.group} = { };
  users.mutableUsers = false;

  environment.etc = {
    "omogen/web.toml".text = ''
      [web]
      secret_key = 'default very insecure key!'

      [database]
      password = 'omogenjudge'

      [email]
      mailjet_api_key = 'fill in api key'
      mailjet_api_secret = 'fill in api secret'

      [staticfiles]
      dir = '${pkgs.pkgsOmogen.omogenjudge-web-static}'
    '';
    "nginx/uwsgi_params".text = ''
      uwsgi_param QUERY_STRING $query_string;
      uwsgi_param REQUEST_METHOD $request_method;
      uwsgi_param CONTENT_TYPE $content_type;
      uwsgi_param CONTENT_LENGTH $content_length;
      uwsgi_param REQUEST_URI $request_uri;
      uwsgi_param PATH_INFO $document_uri;
      uwsgi_param DOCUMENT_ROOT $document_root;
      uwsgi_param SERVER_PROTOCOL $server_protocol;
      uwsgi_param REMOTE_ADDR $remote_addr;
      uwsgi_param REMOTE_PORT $remote_port;
      uwsgi_param SERVER_ADDR $server_addr;
      uwsgi_param SERVER_PORT $server_port;
      uwsgi_param SERVER_NAME $server_name;
    '';
  };

  services.uwsgi = {
    enable = true;
    user = cfg.userweb;
    group = cfg.group;
    plugins = [ "python3" ];
    instance = {
      type = "normal";
      master = true;
      workers = 2;
      socket = cfg.uwsgi-socket;
      module = "omogenjudge.wsgi";
      pythonPackages = self: omogen-python-deps;
    };
  };

  services.nginx = {
    enable = true;

    clientMaxBodySize = "75m";
    logError = "stderr debug";

    virtualHosts.omogenjudge-web = {
      #addSSL = true;
      #enableACME = true;
      serverName = "judge.kodsport.dev";
      serverAliases = [ "*.judge.kodsport.dev" ];

      locations."/static/".alias = "${pkgs.pkgsOmogen.omogenjudge-web-static}/";

      locations."/".extraConfig = ''
        uwsgi_pass ${cfg.uwsgi-socket};
        include    /etc/nginx/uwsgi_params;
      '';
    };
  };

  security.acme = {
    acceptTerms = true;
    defaults.email = "styrelse@chalmerscoding.club";
  };

  services.postgresql = {
    enable = true;
    initialScript = pkgs.writeText "postgresql-initscript" ''
      CREATE DATABASE omogenjudge;

      CREATE ROLE omogenjudge WITH LOGIN PASSWORD 'omogenjudge' CREATEDB;
      GRANT ALL PRIVILEGES ON DATABASE omogenjudge TO omogenjudge;

      CREATE ROLE root;
      GRANT ALL PRIVILEGES ON DATABASE omogenjudge TO root;
    '';

    authentication = ''
      #type database    DBuser      origin-address auth-method
      host  omogenjudge omogenjudge ::1/128        trust
      host  omogenjudge root        ::1/128        trust
    '';

    identMap = ''
      # ArbitraryMapName systemUser DBUser
      superuser_map      uwsgi      omogenjudge
      superuser_map      root       root
    '';
  };

  systemd.services."migrate-db" = {
    enable = true;
    script = ''
      # Sleep to allow the started pg process to initialize.
      sleep 3

      ${pkgs.pkgsOmogen.django-admin}/bin/django-admin migrate
    '';

    requires = [ "postgresql.service" ];
    after = [ "postgresql.service" ];

    requiredBy = [ "uwsgi.service" ];
    wantedBy = [ "uwsgi.service" ];
    before = [ "uwsgi.service" ];

    serviceConfig = { User = "root"; };
  };

  fileSystems."/".fsType = "tmpfs";

  virtualisation = let
    sharedDirectories = {
      "/var/lib/postgresql" = "db";
      "/var/lib/acme" = "certificates";
      "${cfg.var-lib-omogen}" = "problems";
    };
    virtfs = device:
      ''-virtfs local,path="$OMOGEN"/${device},''
      + "security_model=mapped-file,mount_tag=${device}";
  in {
    # Mount in launch script
    qemu.options = lib.attrsets.mapAttrsToList (_: virtfs) sharedDirectories;

    # Mount within VM
    fileSystems = builtins.mapAttrs (_: device: {
      inherit device;
      fsType = "9p";
      neededForBoot = true;
      options = [
        "trans=virtio"
        "version=9p2000.L"
        "msize=${toString config.virtualisation.msize}"
      ];
    }) sharedDirectories;

    forwardPorts = [
      {
        from = "host";
        host.port = 8080;
        guest.port = 80;
      }
      {
        from = "host";
        host.port = 8443;
        guest.port = 443;
      }
    ];
  };
  networking.firewall.allowedTCPPorts = [ 80 443 ];

  system.stateVersion = "23.11";
}
