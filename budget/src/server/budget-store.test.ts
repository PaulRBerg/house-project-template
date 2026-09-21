import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { serializeBudgetDocument } from "../domain/serialization.js";
import { makeDocument } from "../domain/test-fixtures.js";
import { resolveBudgetBackupDirectory } from "./api-vite-plugin.js";
import { BudgetStore, BudgetStoreError } from "./budget-store.js";

describe("BudgetStore", () => {
  let directory: string;
  let documentPath: string;
  let backupDirectory: string;

  beforeEach(async () => {
    directory = await mkdtemp(join(tmpdir(), "house-template-budget-store-"));
    documentPath = join(directory, "project.json");
    backupDirectory = join(directory, "backups");
    await writeFile(documentPath, serializeBudgetDocument(makeDocument()), "utf8");
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  it("saves atomically and can read the result after restart", async () => {
    const store = new BudgetStore({ documentPath, backupDirectory });
    const initial = await store.read();
    const initialBytes = await readFile(documentPath);
    const changed = {
      ...initial.document,
      project: { ...initial.document.project, name: "Casa actualizată" },
    };
    const result = await store.save(initial.revision, changed);
    expect(result.ok).toBe(true);

    const restarted = new BudgetStore({ documentPath, backupDirectory });
    const saved = await restarted.read();
    expect(saved.document.project.name).toBe("Casa actualizată");
    expect(saved.revision).not.toBe(initial.revision);
    expect((await readFile(documentPath, "utf8")).split("\n").length).toBeLessThan(100);
    const backups = await readdir(backupDirectory);
    const firstBackup = backups[0];
    if (firstBackup === undefined) {
      throw new Error("Backup-ul de recuperare lipsește.");
    }
    expect(await readFile(join(backupDirectory, firstBackup))).toEqual(initialBytes);
  });

  it("reads legacy scenarios without writing and saves only the two retained tiers", async () => {
    const document = makeDocument();
    const legacy = JSON.stringify(document).replace('"baseCents":', '"lowCents":9000,"baseCents":');
    await writeFile(documentPath, legacy, "utf8");
    const store = new BudgetStore({ documentPath, backupDirectory });
    const initial = await store.read();
    expect(initial.document).toEqual(document);
    expect(await readFile(documentPath, "utf8")).toBe(legacy);

    expect((await store.save(initial.revision, initial.document)).ok).toBe(true);
    expect(JSON.parse(await readFile(documentPath, "utf8"))).toEqual(document);
    const restarted = new BudgetStore({ documentPath, backupDirectory });
    expect((await restarted.read()).document).toEqual(document);
    expect(await store.save(initial.revision, initial.document)).toMatchObject({
      ok: false,
      conflict: true,
    });
    const [backup] = await readdir(backupDirectory);
    if (backup === undefined) throw new Error("Backup-ul de recuperare lipsește.");
    expect(await readFile(join(backupDirectory, backup), "utf8")).toBe(legacy);
  });

  it("serializes concurrent writes and rejects a stale revision without overwriting", async () => {
    const store = new BudgetStore({ documentPath, backupDirectory });
    const initial = await store.read();
    const firstDocument = {
      ...initial.document,
      project: { ...initial.document.project, name: "Prima salvare" },
    };
    const staleDocument = {
      ...initial.document,
      project: { ...initial.document.project, name: "Salvare depășită" },
    };
    const [first, stale] = await Promise.all([
      store.save(initial.revision, firstDocument),
      store.save(initial.revision, staleDocument),
    ]);
    expect(first.ok).toBe(true);
    expect(stale).toMatchObject({ ok: false, conflict: true });
    expect((await store.read()).document.project.name).toBe("Prima salvare");
  });

  it("bounds recoverable backups", async () => {
    const store = new BudgetStore({ documentPath, backupDirectory, maxBackups: 2 });
    let snapshot = await store.read();
    for (const name of ["Unu", "Doi", "Trei"]) {
      const result = await store.save(snapshot.revision, {
        ...snapshot.document,
        project: { ...snapshot.document.project, name },
      });
      if (!result.ok) throw new Error("Conflict neașteptat în test");
      snapshot = result.snapshot;
    }
    expect((await readdir(backupDirectory)).filter((file) => file.endsWith(".json"))).toHaveLength(
      2,
    );
  });

  it("isolates pruning for two configured document paths", async () => {
    const firstDocumentPath = join(directory, "first.json");
    const secondDocumentPath = join(directory, "second.json");
    await Promise.all([
      writeFile(firstDocumentPath, serializeBudgetDocument(makeDocument()), "utf8"),
      writeFile(secondDocumentPath, serializeBudgetDocument(makeDocument()), "utf8"),
    ]);
    const firstBackupDirectory = resolveBudgetBackupDirectory(directory, firstDocumentPath, true);
    const secondBackupDirectory = resolveBudgetBackupDirectory(directory, secondDocumentPath, true);
    expect(firstBackupDirectory).not.toBe(secondBackupDirectory);
    expect(resolveBudgetBackupDirectory(directory, documentPath, false)).toBe(
      join(directory, ".cache/budget-backups"),
    );

    const firstStore = new BudgetStore({
      documentPath: firstDocumentPath,
      backupDirectory: firstBackupDirectory,
      maxBackups: 2,
    });
    const secondStore = new BudgetStore({
      documentPath: secondDocumentPath,
      backupDirectory: secondBackupDirectory,
      maxBackups: 2,
    });
    let firstSnapshot = await firstStore.read();
    let secondSnapshot = await secondStore.read();
    for (const name of ["Prima 1", "Prima 2", "Prima 3"]) {
      const result = await firstStore.save(firstSnapshot.revision, {
        ...firstSnapshot.document,
        project: { ...firstSnapshot.document.project, name },
      });
      if (!result.ok) throw new Error("Conflict neașteptat pentru primul buget");
      firstSnapshot = result.snapshot;
    }
    for (const name of ["A doua 1", "A doua 2", "A doua 3"]) {
      const result = await secondStore.save(secondSnapshot.revision, {
        ...secondSnapshot.document,
        project: { ...secondSnapshot.document.project, name },
      });
      if (!result.ok) throw new Error("Conflict neașteptat pentru al doilea buget");
      secondSnapshot = result.snapshot;
    }

    expect(await readdir(firstBackupDirectory)).toHaveLength(2);
    expect(await readdir(secondBackupDirectory)).toHaveLength(2);
  });

  it("does not replace malformed or missing files", async () => {
    const malformed = "{ invalid";
    await writeFile(documentPath, malformed, "utf8");
    const store = new BudgetStore({ documentPath, backupDirectory });
    await expect(store.read()).rejects.toMatchObject<Partial<BudgetStoreError>>({
      code: "DATA_FILE_INVALID_JSON",
    });
    expect(await readFile(documentPath, "utf8")).toBe(malformed);

    await rm(documentPath);
    await expect(store.read()).rejects.toMatchObject<Partial<BudgetStoreError>>({
      code: "DATA_FILE_MISSING",
    });
  });

  it("rejects an invalid document before touching disk", async () => {
    const store = new BudgetStore({ documentPath, backupDirectory });
    const snapshot = await store.read();
    const before = await readFile(documentPath, "utf8");
    const invalid = {
      ...snapshot.document,
      project: { ...snapshot.document.project, currency: "RON" },
    };
    expect(() =>
      store.save(snapshot.revision, invalid as unknown as typeof snapshot.document),
    ).toThrow();
    expect(await readFile(documentPath, "utf8")).toBe(before);
  });

  it("keeps the canonical file unchanged when backup creation fails", async () => {
    const store = new BudgetStore({ documentPath, backupDirectory: documentPath });
    const snapshot = await store.read();
    const before = await readFile(documentPath, "utf8");
    await expect(
      store.save(snapshot.revision, {
        ...snapshot.document,
        project: { ...snapshot.document.project, name: "Nu se salvează" },
      }),
    ).rejects.toMatchObject<Partial<BudgetStoreError>>({ code: "BACKUP_FAILED" });
    expect(await readFile(documentPath, "utf8")).toBe(before);
  });
});
