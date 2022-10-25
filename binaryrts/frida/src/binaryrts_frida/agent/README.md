# BinaryRTS TypeScript Frida Agent

The frida agent requires an installation of [NodeJS](https://nodejs.org/en/).

## Build

```shell
npm install
npm run watch  # will continuously transpile agent
```

## Run transpiled JavaScript agent with `frida` directly

```shell
frida -f path/to/executable -l _agent.js
```