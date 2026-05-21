{
  languages.python = {
    enable = true;
    venv.enable = true;

    uv = {
      enable = true;
      sync = {
        enable = true;
        allExtras = true;
      };
    };
  };

  languages.rust.enable = true;

  # Use system git rather than Nix' because of code signing shenanigans on macOS
  env.KARSK_GIT = "/usr/bin/git";
}
