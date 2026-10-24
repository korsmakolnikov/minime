# Print the namespace dependency graph of a compiled Mix application.
#
# Usage (from the project root):
#   mix run --no-start <path>/deps_graph.exs <app> [depth]
#
# Modules are grouped by their first `depth` alias segments (default 2, e.g.
# Sysops.Ticketing). The output lists every group with its module count, then
# every edge between groups with the number of distinct remote calls behind it.
# Dependencies come from the BEAM :imports chunk (remote calls only).

[app | rest] = System.argv()
app = String.to_atom(app)
depth = rest |> List.first("2") |> String.to_integer()

Application.load(app)
modules = Application.spec(app, :modules) || raise "Application #{app} not found"

group_of =
  Map.new(modules, fn module ->
    {module, module |> Module.split() |> Enum.take(depth) |> Enum.join(".")}
  end)

calls = fn module ->
  {:ok, {^module, [imports: imports]}} = :beam_lib.chunks(:code.which(module), [:imports])
  imports
end

sizes = Enum.frequencies(Map.values(group_of))

edges =
  for module <- modules,
      from = group_of[module],
      {target, _fun, _arity} <- calls.(module),
      to = Map.get(group_of, target),
      to != nil and to != from,
      reduce: %{} do
    acc -> Map.update(acc, {from, to}, 1, &(&1 + 1))
  end

IO.puts("# groups (modules)")
for {name, count} <- Enum.sort(sizes), do: IO.puts("#{name}\t#{count}")
IO.puts("# edges (remote calls)")
for {{from, to}, count} <- Enum.sort(edges), do: IO.puts("#{from} -> #{to}\t#{count}")
