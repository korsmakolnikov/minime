defmodule AdlFitness do
  @moduledoc """
  Helpers that turn ADL assertions into ExUnit fitness functions.

  Copied into the project by the `adl-fitness` skill. Dependencies are read
  from the `:imports` chunk of the compiled BEAM files, so they cover remote
  function calls (including macro expansions). They do not see modules that
  are only referenced as atoms or through struct literals; declare a stronger
  tool such as `boundary` in the ADL `REQUIRES` clause when that matters.
  """

  import ExUnit.Assertions

  @doc """
  All modules of `app`, loading the application if needed. Modules compiled
  from the `test/` tree (test support helpers, including this one) are left out.
  """
  def modules(app) do
    Application.load(app)

    case Application.spec(app, :modules) do
      nil -> flunk("Application #{inspect(app)} is not available.")
      modules -> Enum.reject(modules, &test_support?/1)
    end
  end

  defp test_support?(module) do
    source = module.module_info(:compile) |> Keyword.get(:source, ~c"") |> to_string()
    String.contains?(source, "/test/")
  end

  @doc "True when `module` is `namespace` or lives under it. Works for Erlang modules too."
  def within?(module, namespace) do
    module = Atom.to_string(module)
    namespace = Atom.to_string(namespace)
    module == namespace or String.starts_with?(module, namespace <> ".")
  end

  @doc "Modules of `app` that live under `namespace`."
  def modules_within(app, namespace) do
    Enum.filter(modules(app), &within?(&1, namespace))
  end

  @doc "Distinct modules called by `module`, excluding itself."
  def dependencies(module) do
    path = :code.which(module)

    {:ok, {^module, [imports: imports]}} =
      :beam_lib.chunks(path, [:imports])

    imports
    |> Enum.map(fn {mod, _fun, _arity} -> mod end)
    |> Enum.uniq()
    |> Enum.reject(&(&1 == module))
  end

  @doc """
  Guards against vacuous passes: every namespace must contain at least one
  module, otherwise an assertion about it would pass on an empty tree.
  """
  def assert_defined(app, namespaces) do
    for namespace <- List.wrap(namespaces) do
      assert modules_within(app, namespace) != [],
             "ADL artifact #{inspect(namespace)} has no modules in #{inspect(app)}."
    end

    :ok
  end

  @doc """
  ASSERT(CLASSES are only CONTAINED within <namespaces>).

  `allow` lists modules exempt from the rule, such as the root module or the
  OTP application callback.
  """
  def assert_only_within(app, namespaces, opts \\ []) do
    allowed = Keyword.get(opts, :allow, [])
    namespaces = List.wrap(namespaces)

    strays =
      for module <- modules(app),
          module not in allowed,
          not Enum.any?(namespaces, &within?(module, &1)),
          do: module

    assert strays == [],
           "Modules outside #{inspect(namespaces)}: #{inspect(strays)}"
  end

  @doc """
  ASSERT(<from> has NO DEPENDENCY on {<targets>}).
  """
  def assert_no_dependency(app, from, targets) do
    targets = List.wrap(targets)

    violations =
      for module <- modules_within(app, from),
          dependency <- dependencies(module),
          target <- targets,
          within?(dependency, target),
          do: {module, dependency}

    assert violations == [],
           "#{inspect(from)} depends on #{inspect(targets)}: #{inspect(violations)}"
  end

  @doc """
  ASSERT(<from> has NO DEPENDENCY on other <siblings>) applied pairwise:
  each namespace in `namespaces` must not depend on any of the others.
  """
  def assert_mutually_independent(app, namespaces) do
    for from <- namespaces do
      assert_no_dependency(app, from, List.delete(namespaces, from))
    end

    :ok
  end
end
