{pkgs}: {
  deps = [
    pkgs.cairo
    pkgs.mysql-client
    pkgs.mysql
    pkgs.rustc
    pkgs.pkg-config
    pkgs.libxcrypt
    pkgs.libiconv
    pkgs.cargo
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.openssl
  ];
}
