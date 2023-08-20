{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    nixos-generators = {
      url = "github:nix-community/nixos-generators";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, nixos-generators }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        lib = nixpkgs.lib;
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = false;
        };

        pkgsOmogen = import ./nix/packages.nix { inherit lib pkgs; };
      in {
        devShell =
          pkgs.mkShell { nativeBuildInputs = with pkgs; [ bashInteractive ]; };

        # To run in qemu-kvm
        packages = {
          inherit (pkgsOmogen)
            python3-omogenjudge frontend_assets omogenjudge-web omogenjudge-queue omogenjudge-host;

          monolith-vm = nixos-generators.nixosGenerate {
            inherit system;
            modules = [
              { nixpkgs.overlays = [ (final: prev: { inherit pkgsOmogen; }) ]; }
              ./nix/monolith-vm.nix
            ];
            format = "vm-nogui";
          };
        };
      });
}
