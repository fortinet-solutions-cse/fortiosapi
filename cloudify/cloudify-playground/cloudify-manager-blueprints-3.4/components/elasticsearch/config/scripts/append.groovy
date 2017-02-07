if (ctx._source.containsKey(key))
 {ctx._source[key] += value;}
 else {ctx._source[key] = [value]}