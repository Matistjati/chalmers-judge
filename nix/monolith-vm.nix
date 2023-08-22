{ lib, pkgs, ... }:
let
  cfg = {
    statedir = "/var/lib/omogen";
    userweb = "omogen-web";
    group = "omogen";
  };
in {
  users.users = {
    root = {
      password = " ";
      packages = [ pkgs.pkgsOmogen.python3-omogenjudge ];
    };
    omogen-web = {
      isSystemUser = true;
      group = cfg.group;
    };
  };
  users.groups.${cfg.group} = { };
  users.mutableUsers = false;

  system.activationScripts.makeWebStateDir = ''
    mkdir -p ${cfg.statedir}
    chown omogen-web:omogen ${cfg.statedir}
    chmod 644 ${cfg.statedir}
  '';

  environment.etc."nginx/uwsgi_params".text = ''
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

  virtualisation.forwardPorts = [
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
  networking.firewall.allowedTCPPorts = [ 80 443 ];

  services.uwsgi = {
    enable = true;
    user = cfg.userweb;
    group = cfg.group;
    instance = {
      type = "normal";
      master = true;
      workers = 2;
      http = "127.0.0.1:62542";
      module = "omogenjudge.wsgi";
      #chdir = cfg.statedir;
      pythonPackages = self: pkgs.pkgsOmogen.python3-omogenjudge;
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
        uwsgi_pass 127.0.0.1:62542;
        include    /etc/nginx/uwsgi_params;
      '';
    };
  };

  security.acme = {
    acceptTerms = true;
    defaults.email = "styrelse@chalmerscoding.club";
  };

  system.stateVersion = "23.11";
}
