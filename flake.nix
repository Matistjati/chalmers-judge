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

        packages = import ./nix/packages.nix { inherit lib pkgs; };

      in {
        devShell = pkgs.mkShell {
          nativeBuildInputs = let p = pkgs; in [ p.bashInteractive ];
        };

        # To run in qemu-kvm
        packages = packages.pkgsOmogen // {
          monolith-vm = nixos-generators.nixosGenerate {
            inherit system;
            modules = [
              {
                nixpkgs.overlays =
                  [ (final: prev: { inherit (packages) pkgsOmogen; }) ];
              }
              ./nix/monolith-vm.nix
            ];
            specialArgs.omogen-python-deps = packages.omogen-python-deps;
            format = "vm-nogui";
          };
        };
      });
}
